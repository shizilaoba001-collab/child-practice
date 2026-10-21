---
name: child-practice
description: 根据儿童实际学习进度和错题反馈建立本地学习档案，设计语文数学变式练习，生成题目与独立家长答案PDF。用于家长自助练习，不用于评级诊断或代替完整学校教学。
---

# 儿童错题练习助手 · 分享版 0.1.1

由宿主AI承担读题、分析与创作；本包脚本承担本地档案、反馈关联和可打印PDF。没有模型API、自动聊天服务或后台任务。只读本家庭主动提供的材料；资料保存到当前工作文件夹的`user-data/`，不写进Skill安装目录、不上传Git。

## 第一次使用

1. 读[安装说明](references/install.md)及包内requirements.txt；在宿主可执行Python的环境，用Python 3.9+创建独立虚拟环境并安装依赖。运行`scripts/practice.py doctor`核包内字体和依赖。执行路径按当前Skill实际位置解析，不猜用户电脑路径。安装失败明确缺件，不假装能输出文件。
2. 一次最多问3个容易回答的问题：年级、要练的语数当前进度（也可发最近一页练习）、合适练习量。不要让家长先做错因分析或设计教学。不确定的进度保留未知，不只按年龄加难。
3. 使用代号建档，不索取真实姓名/学校；每孩独立代号。把家长确认的页数、范字数、遍数传给init。没有既定量时先给较轻建议让家长选择，不把示例4页当每人强制标准。

## 每次工作

1. `context`读取所选孩子当前进度、已出内容、recent_feedback（包括独立做对但没新增焦点的反馈）和带具体原题/实际反馈的active_focus；不能凭聊天记忆覆盖文件。反馈来自哪一卷哪道题要明确。
2. 设计新题，数学混合数位/计算/关系/规律/图形等已学能力，换情境、条件、问法和作答形式，不只换数字。按已确认基线小步变化；不会的先定位，不靠大量重做同题升难。
3. 语文以圈/连/填/写为主，组词/短答允许汉字拼音混写。新范字先看recent_writing轮换，薄弱字确需重练时注明review_reason，保持已定遍数。低年级题干按实际需要注音，含标题和要求；使用ruby块明确填写读音，核多音字/轻声/ü，不让程序猜读音。
4. 遇“判断并改正/先圈再写/写两种”，按动作留痕；漏动作不统一归为粗心。组数分数位、0占位、使用次数、排列和条件；代读仍不懂时查概念。两种选法须区分不同组合与交换先后。比较关系先看算式再看计算。原答案不清则保持未知。
5. 拼音认选、独立拼读、看字认读、临写、独写分开；圈对/写对不等于会拼读。错误多时缩到少量核心音节，配必要抽读定位，示范一处后撤提示再试；不增加全范围大测/长讲/抄写。家长估计比例不是逐题成绩，不诊断能力障碍。
6. 按[题包格式](references/formats.md)写本批JSON，含当前child_id/context_sha256，题目 blocks、答案answer和必要parent_note。每个active_focus在feedback_application对应题面practice、观察observe或说明理由/下次触发的defer；不是每卷全塞一遍。不得把家长承担的观察设计推回家长。
7. `build`实际生成questions.pdf和answers.pdf。核题义、计算、答案与实际渲染，发现溢出调整题包用新issue_id重做，不伪造已打印。脚本核身份/反馈版本/位置，不判断真实教学难度。生成后给两份文件，不只给“生成成功”文字。

## 收到反馈

保留原话、实际答法、帮助程度及家长解释，区别事实和推测。阅读答卷时看不清才补问该处，不索取全套背景。由AI据[反馈格式](references/formats.md)写反馈JSON并调用feedback，不让家长编辑JSON。未做题不是不会；有可靠独立迁移证据才resolved_focus_ids解除焦点，不因出过新卷清除。下一次context自动带原题与反馈；家长可在新聊天要求继续，Agent仍读本地文件。

停止于本次请求和已确认练习量；忙碌可分段/轮换，不惩罚加量、不无限讲错。只生成文件不声称孩子已会。当前版只验证语数纸笔及简单矢量图，不承诺围棋、晨读原著、音视频或任意聊天平台兼容。

## 脚本命令

以下`<skill>`与`<python>`由AI按实际安装位置/虚拟环境替换，家长不需手填。所有学习数据位于家长选择的工作目录：

```text
<python> <skill>/scripts/practice.py doctor
<python> <skill>/scripts/practice.py init --workspace ./user-data --child learner-1 --label 孩子A --grade 一年级 --chinese-progress <已学内容> --math-progress <已学内容> --pages <已确认偶数页> --writing-count <已确认字数> --copies <已确认遍数>
<python> <skill>/scripts/practice.py context --workspace ./user-data --child learner-1 --output ./user-data/context.json
<python> <skill>/scripts/practice.py build --workspace ./user-data --child learner-1 --packet ./user-data/本批题包.json
<python> <skill>/scripts/practice.py feedback --workspace ./user-data --child learner-1 --input ./user-data/本次反馈.json
```
