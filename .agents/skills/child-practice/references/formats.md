# 题包和反馈格式（由AI编写，家长不填JSON）

先context，使用返回的child_id、context_sha256和settings。读取recent_feedback中最近3条完整反馈（包含没有新增薄弱点的独立做对记录）；更早未解决的薄弱点仍在active_focus中，历史完整反馈留在本孩子feedback目录。完整可运行的合成示例见仓库tests/smoke.py；不是模板题库，不把测试题当每次新题。

## 题包

```json
{
  "child_id": "learner-1",
  "context_sha256": "从本次context返回值复制",
  "issue_id": "20261021-a",
  "date": "2026-10-21",
  "response_mode": "written",
  "writing": {"characters": [], "copies_each": 1},
  "pages": [{"subject": "语文", "questions": [{
    "id": "C1", "title": "圈出正确拼音",
    "blocks": [{"type": "text", "text": "女：nǚ / nǔ"}],
    "answer": "nǚ", "parent_note": "必要时抽读，圈对不证明会独立拼读。"
  }]}],
  "feedback_application": []
}
```

以上仅字段片段，完整题包必须符合孩子的页数、范字数量/遍数，语文页在前数学页在后；每题ID全卷唯一，数学题含task_type，至少混合两种能力。每题answer为文字答案，可含步骤和合理多解；parent_note为必要观察/带练法。程序不检查算术或知识结论，AI须先自行核对。

每个反馈焦点对应一项application：
- `{"focus_id":"从context读取", "mode":"practice", "question_ids":["M1"], "note":"新题如何针对这点"}`
- mode=`observe`：题目须有对应parent_note，不凭题目作答替代实际读音检查。
- mode=`defer`：填写note理由及next_trigger下次触发；允许轮换，不强塞所有薄弱点。

## 孩子题面blocks

- `text`：`text`字符串，可选size(默认14)、leading(默认23)。普通段落自动折行。
- `ruby`：`units`为`{"text":"字或短词", "pinyin":"对应读音"}`数组；一字或短词为单位，自动换行。读音由AI明确输入，不自动猜。标点可省pinyin。
- `blank`：lines为1—6，绘制答题线；仅需圈选时不额外加空线。
- `copy_grid`：characters为范字列表、copies_each为1—5；每字首格嵌范字，后面各格写一遍。实际范字列表须与顶层writing相符。
- `table`：rows为规则矩形二维字符串数组；文字过宽报错。
- `diagram`：height为20—250pt，objects为rect/circle/line/text数组。以本图左下为原点，x/y均pt，宽约519pt。rect有width/height；circle有radius；line有x2/y2；text有text及可选size。不执行任意代码，不载远端图片。复杂图示先用可表达的简单矢量，不声称支持所有数学绘图。

页面过长会报错，AI重新分配内容或缩短题面，不把答案裁到纸外；总页数/练习量改动先依家长选择。答案自动分页，不与孩子题目混排。每次使用新issue_id，旧卷/反馈不覆盖。

## 反馈

```json
{
  "child_id": "learner-1",
  "issue_id": "20261021-a",
  "feedback_id": "20261021-f1",
  "observations": [{
    "question_id": "C1",
    "result": "incorrect",
    "actual_answer": null,
    "parent_report": "孩子圈错了，暂时没有听他实际拼读。",
    "parent_interpretation": "家长认为没有认真看，尚未证实。",
    "next_requirement": "区分拼音认选和独立拼读，少量换词再看。"
  }]
}
```

result可取independent_correct/assisted_correct/incorrect/omitted/not_attempted/unknown。actual_answer不清则null。脚本自动把该卷原题完整绑定入反馈，再让带next_requirement的观察成为active_focus。未作答本身不代表不会，不必都添加练习焦点。

有具体独立迁移证据才用resolved_focus_ids解除旧焦点，同时提供resolution_evidence；新反馈不会静默擦掉旧反馈。教学进度更新：AI与家长核准后修改本孩子profile.progress，保留修改前副本；不要写成已掌握。
