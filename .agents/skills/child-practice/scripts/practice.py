#!/usr/bin/env python3
"""Local-only learner records and printable practice. AI supplies teaching decisions and questions."""
import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 1


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.writing-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def child_dir(workspace, child):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}', child):
        raise ValueError('child应为简短英文代号，如 learner-1；不需要真实姓名')
    return Path(workspace).resolve() / 'learners' / child


def load(workspace, child):
    path = child_dir(workspace, child) / 'profile.json'
    data = read(path)
    if data.get('child_id') != child:
        raise ValueError('学习档案身份不符')
    return path, data


def context(workspace, child):
    path, profile = load(workspace, child)
    issues = []
    for issue_id in profile['issues'][-2:]:
        issue = read(path.parent / 'issues' / (issue_id + '.json'))
        issues.append({'issue_id': issue_id, 'date': issue['date'], 'questions': issue['pages'],
                       'writing': issue.get('writing'), 'status': issue['status']})
    recent_feedback = [read(path.parent / 'feedback' / (fid + '.json')) for fid in profile['feedback'][-3:]]
    body = {'recent_feedback': recent_feedback, 'child_id': child, 'settings': profile['settings'], 'grade': profile['grade'],
            'progress': profile['progress'], 'active_focus': profile['active_focus'],
            'recent_writing': profile['writing_history'], 'recent_issues': issues}
    return {'schema_version': SCHEMA, **body, 'context_sha256': digest(body),
            'instructions': '按实际反馈出新题；未知原因保持未知。每个焦点在应用表注明练习、观察或轮换，不用凑题加量。'}


def init(args):
    path = child_dir(args.workspace, args.child) / 'profile.json'
    if path.exists():
        raise ValueError('档案已存在，用context继续，不覆盖')
    if args.pages < 2 or args.pages % 2:
        raise ValueError('双科题面页数须为大于等于2的偶数')
    if args.writing_count < 0 or not 1 <= args.copies <= 5:
        raise ValueError('范字数须非负，临写遍数须1—5，与渲染器一致')
    profile = read(ROOT / 'references' / 'blank-profile.json')
    profile.update(child_id=args.child, label=args.label or args.child, grade=args.grade,
                   progress={'语文': args.chinese_progress, '数学': args.math_progress})
    profile['settings'] = {'pages': args.pages, 'writing_count': args.writing_count,
                           'copies_each': args.copies, 'response_mode': 'written'}
    write(path, profile)
    return {'status': 'created', 'child_id': args.child, 'next': 'context', 'actual_answers': '尚无'}


def issue_name(s):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,59}', s):
        raise ValueError('issue_id须英文数字短代号，如 20261021-a')
    return s


def validate_packet(packet, ctx):
    if packet.get('child_id') != ctx['child_id']:
        raise ValueError('题包与所选孩子不符')
    if packet.get('context_sha256') != ctx['context_sha256']:
        raise ValueError('题包未用当前学习档案/反馈，请重新context')
    issue_name(packet['issue_id'])
    date.fromisoformat(packet['date'])
    if packet.get('response_mode') != 'written':
        raise ValueError('双科卷须主要由孩子动笔')
    settings = ctx['settings']
    pages = packet['pages']
    half = settings['pages'] // 2
    if [p['subject'] for p in pages] != ['语文'] * half + ['数学'] * half:
        raise ValueError('实际页数/语数顺序不符合该孩子设置')
    writing = packet['writing']
    chars = writing['characters']
    if len(chars) != settings['writing_count'] or len(set(chars)) != len(chars) or writing['copies_each'] != settings['copies_each']:
        raise ValueError('范字数量/遍数与该孩子设置不符')
    recent = {ch for row in ctx['recent_writing'][-5:] for ch in row['characters']}
    if recent & set(chars) and not writing.get('review_reason'):
        raise ValueError('近期范字重复；需轮换，或具体注明为什么复练')
    refs, types, grid_chars = set(), set(), []
    for page in pages:
        if not page['questions']:
            raise ValueError('不以空白页凑页数')
        for q in page['questions']:
            if not re.fullmatch(r'[A-Za-z0-9_-]+', q['id']) or q['id'] in refs:
                raise ValueError('题号缺失/重复或格式无效')
            refs.add(q['id'])
            if not q.get('answer') or not q.get('blocks'):
                raise ValueError('每题须有孩子题面和独立答案')
            if page['subject'] == '数学':
                types.add(q['task_type'])
            for block in q['blocks']:
                if block['type'] == 'copy_grid':
                    grid_chars.extend(block['characters'])
                    if block['copies_each'] != settings['copies_each']:
                        raise ValueError('题面临写格数与设置不符')
    if grid_chars != chars:
        raise ValueError('实际范字格与范字声明不一致')
    if len(types) < 2:
        raise ValueError('数学须混合能力，不全卷一个类型')
    focus_ids = {f['id'] for f in ctx['active_focus']}
    apps = packet.get('feedback_application', [])
    if len(apps) != len(focus_ids) or {a['focus_id'] for a in apps} != focus_ids:
        raise ValueError('漏用或重复记录当前反馈焦点')
    for item in apps:
        if not item.get('note'):
            raise ValueError('说明怎样练/怎样观察/为何轮换')
        if item['mode'] in ['practice', 'observe']:
            if not item.get('question_ids') or not set(item['question_ids']) <= refs:
                raise ValueError('反馈指向不存在的实际题号')
            if item['mode'] == 'observe' and not any(q.get('parent_note') for p in pages for q in p['questions'] if q['id'] in item['question_ids']):
                raise ValueError('家长观察须落入对应题的parent_note')
        elif item['mode'] == 'defer':
            if not item.get('next_trigger'):
                raise ValueError('轮换延后须说明下次触发')
        else:
            raise ValueError('反馈mode须practice/observe/defer')


def build(args):
    from render import render
    path, profile = load(args.workspace, args.child)
    ctx = context(args.workspace, args.child)
    packet = read(args.packet)
    validate_packet(packet, ctx)
    issue_id = packet['issue_id']
    issue_path = path.parent / 'issues' / (issue_id + '.json')
    target = path.parent / 'outputs' / issue_id
    if issue_path.exists() or target.exists():
        raise ValueError('该issue已存在；请用新的issue_id，不覆盖旧卷')
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.render-', dir=target.parent))
    try:
        result = render(packet, staging, profile['label'])
        os.replace(staging, target)
    except Exception:
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
        raise
    saved = copy.deepcopy(packet)
    saved.update(status='generated_not_answered', output_files={'questions': 'questions.pdf', 'answers': 'answers.pdf'},
                 answer_page_count=result['answer_pages'])
    write(issue_path, saved)
    profile['issues'].append(issue_id)
    profile['writing_history'].append({'issue_id': issue_id, 'characters': packet['writing']['characters'], 'state': 'issued_not_mastered'})
    write(path, profile)
    return {'status': 'generated_not_answered', 'issue_id': issue_id, 'child_id': args.child,
            'question_pages': len(packet['pages']), 'answer_pages': result['answer_pages'],
            'questions': str(target / 'questions.pdf'), 'answers': str(target / 'answers.pdf')}


def feedback(args):
    path, profile = load(args.workspace, args.child)
    data = read(args.input)
    if data.get('child_id') != args.child:
        raise ValueError('反馈孩子不符')
    iid = issue_name(data['issue_id'])
    if iid not in profile['issues']:
        raise ValueError('反馈未绑定已出原卷')
    issue = read(path.parent / 'issues' / (iid + '.json'))
    byid = {q['id']: q for p in issue['pages'] for q in p['questions']}
    fid = issue_name(data['feedback_id'])
    destination = path.parent / 'feedback' / (fid + '.json')
    if destination.exists():
        raise ValueError('反馈编号已存在，保留旧记录，用新编号补充')
    if not data.get('observations'):
        raise ValueError('反馈不能为空')
    new_focus = []
    enriched = copy.deepcopy(data)
    for i, obs in enumerate(enriched['observations']):
        if obs['question_id'] not in byid:
            raise ValueError('反馈题号不属于该原卷')
        if obs['result'] not in ['independent_correct', 'assisted_correct', 'incorrect', 'omitted', 'not_attempted', 'unknown']:
            raise ValueError('未知作答状态')
        if not obs.get('parent_report'):
            raise ValueError('保留家长原话或实际反馈')
        obs['original_question'] = byid[obs['question_id']]
        obs['actual_answer'] = obs.get('actual_answer')
        obs['cause_status'] = 'unknown_unless_supported_by_actual_work'
        # Not attempted is recorded, but is not itself proof of a learning weakness.
        if obs.get('next_requirement'):
            new_focus.append({'id': fid + '-' + str(i + 1), 'source_issue': iid,
                              'source_feedback': fid, 'observation': obs,
                              'requirement': obs['next_requirement']})
    resolved = set(data.get('resolved_focus_ids', []))
    if not resolved <= {f['id'] for f in profile['active_focus']}:
        raise ValueError('解除焦点不属于该孩子')
    if resolved and not data.get('resolution_evidence'):
        raise ValueError('解除焦点须记录具体独立表现证据，不因新卷生成自动解除')
    profile['active_focus'] = [f for f in profile['active_focus'] if f['id'] not in resolved] + new_focus
    profile['feedback'].append(fid)
    enriched['source_packet_sha256'] = digest(issue)
    write(destination, enriched)
    issue['status'] = 'feedback_received_not_mastered'
    issue.setdefault('feedback_ids', []).append(fid)
    write(path.parent / 'issues' / (iid + '.json'), issue)
    write(path, profile)
    return {'status': 'feedback_saved', 'child_id': args.child, 'active_focus_count': len(profile['active_focus']), 'next': 'context'}


def doctor(args):
    import reportlab
    import pypdf
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font = ROOT / 'assets/fonts/LearningSerifSC.ttf'
    pdfmetrics.registerFont(TTFont('PracticeCheck', str(font)))
    return {'status': 'ready', 'python': sys.version.split()[0], 'reportlab': reportlab.Version,
            'pypdf': pypdf.__version__, 'font': 'bundled LearningSerifSC (SIL OFL)',
            'external_ai_api': 'not_used; host AI authors questions'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    for name in ['init', 'context', 'build', 'feedback']:
        p = sub.add_parser(name)
        p.add_argument('--workspace', required=True, type=Path)
        p.add_argument('--child', required=True)
        if name == 'init':
            p.add_argument('--label', default='')
            p.add_argument('--grade', required=True)
            p.add_argument('--chinese-progress', required=True)
            p.add_argument('--math-progress', required=True)
            p.add_argument('--pages', required=True, type=int)
            p.add_argument('--writing-count', required=True, type=int)
            p.add_argument('--copies', required=True, type=int)
        elif name == 'context':
            p.add_argument('--output', type=Path)
        elif name == 'build':
            p.add_argument('--packet', required=True, type=Path)
        else:
            p.add_argument('--input', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = context(args.workspace, args.child) if args.command == 'context' else globals()[args.command](args)
        if args.command == 'context' and args.output:
            write(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, ImportError) as exc:
        parser.exit(2, '未完成：' + str(exc) + '\n')


if __name__ == '__main__':
    main()
