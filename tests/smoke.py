#!/usr/bin/env python3
"""Synthetic two-issue lifecycle; no real learner data or hosted AI calls."""
import argparse
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / '.agents/skills/child-practice/scripts/practice.py'

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def q(i, title, prompt, answer, task=None, note=None, extra=None):
    out = {'id': i, 'title': title, 'blocks': [{'type': 'text', 'text': prompt}], 'answer': answer}
    if extra is not None:
        out['blocks'] += extra
    else:
        out['blocks'].append({'type': 'blank', 'lines': 1})
    if task:
        out['task_type'] = task
    if note:
        out['parent_note'] = note
    return out


def make_packet(ctx, second=False):
    chars = list('太少牙尺' if second else '王玉正早')
    c1 = q('C1', '看拼音圈字', 'nǚ：女 / 牛；lù：路 / 绿。' if not second else 'lǜ：路 / 绿；nǚ hái：女孩 / 男孩。',
           '女、路。' if not second else '绿、女孩。', note='先看独立圈选；收卷后只抽读nǚ、lù或lǜ，不先领读。临写对不证明会拼读，读音未听到就保留未知。')
    c2 = q('C2', '看新范字，各临写两遍', '', '按范字临写两遍，不把临写当独写。',
           extra=[{'type': 'copy_grid', 'characters': chars, 'copies_each': 2}])
    c3 = q('C3', '读句子填空', '', '门口。', extra=[{'type': 'ruby', 'units': [
        {'text': '小', 'pinyin': 'xiǎo'}, {'text': '兔', 'pinyin': 'tù'}, {'text': '在', 'pinyin': 'zài'},
        {'text': '门', 'pinyin': 'mén'}, {'text': '口', 'pinyin': 'kǒu'}, {'text': '。'},
    ]}, {'type': 'text', 'text': '小兔在哪里？（　　　　）'}])
    c4 = q('C4', '组词', '请用“早”和“少”各写一个词，不会写的字可以用拼音。', '早上、多少等合理词均可，汉字拼音混写可。')
    c5 = q('C5', '先圈，再写', '先圈“门”，再写“口”：门　口　田。', '圈门，再写口；两个动作分别看。')
    c6 = q('C6', '写一句话', '用“我会”写一句话，不会写的字可用拼音。', '合理完整句即可，如“我会跳绳”。')
    if not second:
        first = [q('M1', '判断并改正', '对的写“对”，错的改正结果。35−17＝28；26＋19＝45。', '35−17＝18，改正；第二式对。', 'calculation_and_instruction'),
                 q('M2', '看图补全', '补一个同样大的小正方形，使它成为长方形；补后共几格？', '补右下格，共6格。', 'geometry', extra=[{'type':'diagram','height':65,'objects':[{'type':'rect','x':j*25,'y':i*25+5,'width':25,'height':25} for i,j in [(0,0),(0,1),(1,0),(1,1),(1,2)]]}, {'type':'blank','lines':1}]),
                 q('M3', '找规律', '3，6，9，12，（　），（　）。', '15、18。', 'pattern'),
                 q('M4', '数位', '7个十和2个一组成（　）。', '72。', 'place_value'),
                 q('M5', '长度比较', '红绳35厘米，蓝绳19厘米。红绳比蓝绳长多少厘米？', '35−19＝16厘米。', 'comparison'),
                 q('M6', '排队', '小林前面3人，后面5人，一共几人？', '3＋1＋5＝9人。', 'position')]
        last = [q('M7', '按条件组数', '用1、4、0各一次，组成大于100小于400的三位数，写出两种。', '104、140。', 'number_conditions'),
                q('M8', '看表求差', '梨比苹果多多少个？先写算式，再计算。', '32−17＝15个。', 'table_comparison', extra=[{'type':'table','rows':[['苹果','梨'],['17','32']]},{'type':'blank','lines':1}]),
                q('M9', '求原来', '送出12张卡片还剩18张，原来几张？', '18＋12＝30张。', 'inverse'),
                q('M10', '分一分', '8个球，每盒4个，可以装几盒？可画图。', '2盒。', 'grouping'),
                q('M11', '找两种选法', '从11、14、19、16中选两个，和为30。写两种不同选法。', '11＋19、14＋16，交换顺序仍是一种。', 'distinct_pairs'),
                q('M12', '变化后比较', '红球14，蓝球20，增加9个红球，现在谁多，多几个？', '红23，蓝20，红多3。', 'changed_comparison')]
    else:
        first = [q('M1', '先选，再改正', '先圈出结果错误的一式，再把它改正：43−18＝35；24＋17＝41。', '圈第一式，改为43−18＝25；不要只圈不改。', 'calculation_and_instruction'),
                 q('M2', '画图比较', '画3个圆、5个小方格，圈出数量更多的一组。', '圈小方格组。', 'geometry'),
                 q('M3', '规律换方向', '18，15，12，9，（　），（　）。', '6、3。', 'pattern'),
                 q('M4', '拆数', '64里面有几个十、几个一？', '6个十、4个一。', 'place_value'),
                 q('M5', '补到同样多', '甲盒23个珠子，乙盒38个。甲盒再放几个才同样多？', '38−23＝15。', 'comparison'),
                 q('M6', '名次求总数', '从前第3、从后第5，这一队一共几人？', '3＋5−1＝7。', 'position')]
        last = [q('M7', '先定百位，再交换', '用0、2、7各一次，百位放2。写出两种数，再圈较大的。', '207、270，圈270。', 'number_conditions',note='用卡片先固定百位；区分数位与余下两数互换，不把代读仍卡当成不认真。'),
                q('M8', '先选算式，再算', '长绳41厘米，短绳26厘米，相差多少？先圈41＋26 / 41−26，再算。', '圈41−26，算得15厘米。', 'operation_then_calculation',note='圈式对但算错和关系选错分开记录。'),
                q('M9', '变化前后', '原有29张卡片，收回一些后有45张，收回几张？', '45−29＝16。', 'inverse'),
                q('M10', '图形重复', '圆、方、方、圆、方、方、（　）、（　）。', '圆、方。', 'pattern'),
                q('M11', '购物两种买法', '彩笔13元、画本17元、贴纸6元、拼图24元。选两件正好30元，写两种。', '13＋17、6＋24；交换先后不算新组合。', 'distinct_pairs',note='漏一组、同组换序重复、配错与算错分别记。'),
                q('M12', '移动影响两边', '甲盒12，乙盒19，从乙拿4个放甲，现在哪盒多，多几个？', '甲16乙15，甲多1。', 'transfer')]
    packet = {'child_id':ctx['child_id'], 'context_sha256':ctx['context_sha256'], 'issue_id':'demo-b' if second else 'demo-a',
              'date':'2026-10-22' if second else '2026-10-21','response_mode':'written',
              'writing':{'characters':chars,'copies_each':2}, 'pages':[{'subject':'语文','questions':[c1,c2,c3]}, {'subject':'语文','questions':[c4,c5,c6]},
              {'subject':'数学','questions':first}, {'subject':'数学','questions':last}], 'feedback_application':[]}
    if second:
        maps = {'M1':('practice','M1'),'M7':('practice','M7'),'M8':('practice','M8'),'M11':('practice','M11'),'C1':('observe','C1')}
        for f in ctx['active_focus']:
            mode, target = maps[f['observation']['question_id']]
            packet['feedback_application'].append({'focus_id':f['id'],'mode':mode,'question_ids':[target],
                'note':f['requirement']})
    return packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace.exists():
        raise SystemExit('测试必须从不存在的空目录开始，不能覆盖旧运行')
    workspace.mkdir(parents=True)
    records = []
    def call(*items, ok=True):
        result = subprocess.run([sys.executable,str(CLI),*map(str,items)],capture_output=True,text=True,cwd=workspace)
        if (result.returncode==0)!=ok:
            raise AssertionError((items,result.stdout,result.stderr))
        return json.loads(result.stdout) if ok else result.stderr.strip()
    base=['--workspace',workspace,'--child','demo-learner']
    call('doctor')
    call('init',*base,'--label','示例学习者','--grade','一年级','--chinese-progress','已学基础拼音和简单字，具体弱项待观察',
         '--math-progress','已学百以内加减、三位数数位和简单图形','--pages',4,'--writing-count',4,'--copies',2)
    ctx1=call('context',*base)
    assert not ctx1['active_focus'] and not ctx1['recent_issues']
    p1=make_packet(ctx1)
    save(workspace/'packet-a.json',p1)
    first=call('build',*base,'--packet',workspace/'packet-a.json')
    first_files=[Path(first[x]) for x in ['questions','answers']]
    before=[p.read_bytes() for p in first_files]
    feedback={'child_id':'demo-learner','issue_id':'demo-a','feedback_id':'feedback-a','observations':[]}
    for qid,report,req in [
        ('M1','只判断，没有改正；原算式如何算未知','把两个动作分别留痕，不反复空检查'),
        ('M7','成人读题后仍卡，实际填写未知','固定百位再排余下卡片，区分数位和条件'),
        ('M8','差算错，原式未提供','运算选择和计算分开留痕'),
        ('M11','没有给出两组，实际是漏写还是重复未知','在新情境找两种不同组合，交换顺序不算另一种'),
        ('C1','拼音圈选有错，临写对，但未抽读','少量核心音节独立抽读，与临写和认字分开')]:
        feedback['observations'].append({'question_id':qid,'result':'omitted' if qid=='M1' else 'incorrect',
            'actual_answer':None,'parent_report':report,'next_requirement':req})
    save(workspace/'feedback-a.json',feedback)
    call('feedback',*base,'--input',workspace/'feedback-a.json')
    ctx2=call('context',*base)
    assert ctx2['context_sha256']!=ctx1['context_sha256'] and len(ctx2['active_focus'])==5
    assert all(f['observation']['original_question']['id']==f['observation']['question_id'] for f in ctx2['active_focus'])
    p2=make_packet(ctx2,True)
    # Real CLI rejects swapped identity, stale context and silently discarded feedback before output.
    for name,mutator in [('wrong-child',lambda x:x.update(child_id='another-child')),
                         ('stale-context',lambda x:x.update(context_sha256=ctx1['context_sha256'])),
                         ('missing-focus',lambda x:x['feedback_application'].pop())]:
        bad=copy.deepcopy(p2);bad['issue_id']=name;mutator(bad);save(workspace/(name+'.json'),bad)
        reason=call('build',*base,'--packet',workspace/(name+'.json'),ok=False)
        assert not (workspace/'learners/demo-learner/outputs'/name).exists()
        records.append({'case':name,'result':'rejected','reason':reason})
    save(workspace/'packet-b.json',p2)
    second=call('build',*base,'--packet',workspace/'packet-b.json')
    assert before==[p.read_bytes() for p in first_files]
    for output in [first,second]:
        assert len(PdfReader(output['questions']).pages)==4
        assert '示例学习者' in PdfReader(output['questions']).pages[0].extract_text()
        assert len(PdfReader(output['answers']).pages)>=1
    text=''.join(p.extract_text() for p in PdfReader(second['questions']).pages)
    atext=''.join(p.extract_text() for p in PdfReader(second['answers']).pages)
    assert '先定百位' in text and '购物两种买法' in text and '先选算式' in text
    assert '临写对不证明会拼读' in atext
    profile=json.loads((workspace/'learners/demo-learner/profile.json').read_text())
    assert len(profile['issues'])==2 and len(profile['active_focus'])==5
    assert profile['writing_history'][0]['characters']!=profile['writing_history'][1]['characters']
    records.append({'case':'empty-init-first-issue-feedback-second-issue','result':'passed',
        'first_questions':str(Path(first['questions']).relative_to(workspace)),
        'first_answers':str(Path(first['answers']).relative_to(workspace)),
        'second_questions':str(Path(second['questions']).relative_to(workspace)),
        'second_answers':str(Path(second['answers']).relative_to(workspace)),
        'focus_count':5,'old_files_unchanged':True})
    save(workspace/'verification.json',{'status':'passed','synthetic_data':True,'host_model_called':False,'tests':records})
    print(json.dumps({'status':'passed','workspace':str(workspace),'tests':len(records)},ensure_ascii=False))


if __name__=='__main__':
    main()
