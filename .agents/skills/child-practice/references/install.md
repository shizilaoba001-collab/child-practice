# 安装与宿主边界

Skill整体目录含SKILL.md、scripts、references、assets和requirements.txt；不能仅下载SKILL.md。依赖和字体均按Skill自身位置解析，无外部个人路径。

在家长工作目录创建`.venv`并安装：`python -m pip install -r <实际Skill目录>/requirements.txt`。依赖安装到该虚拟环境，不改全机Python。之后使用该虚拟环境的解释器运行`<实际Skill目录>/scripts/practice.py doctor`，就绪后建档。

macOS/Linux解释器一般为`.venv/bin/python`，Windows一般为`.venv/Scripts/python.exe`。先识别实际Python，不照抄不存在的路径。缺Python或联网不可用时，说明实际缺件，不伪造PDF。

数据存家长工作目录的user-data，不存Skill目录；脱离仓库单独安装仍可选任意本地工作目录。没有常驻服务和网络端口，无须API密钥。题目由宿主AI创作，程序只管参数/关联和PDF，不是随机题库或自带模型。
