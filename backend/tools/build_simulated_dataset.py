from __future__ import annotations

import csv
import json
import random
from pathlib import Path


RANDOM_SEED = 20260519
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


CONCEPTS = {
    "C001": ("一元一次方程", "理解只含一个未知数且未知数次数为 1 的方程，能够通过移项、合并同类项、系数化为 1 等步骤求解。", ["移项时忘记变号", "系数化为 1 时除错数", "没有把解代回原方程检验"], ["每一步变形都写清依据", "求解后代回原方程检验", "重点练习含括号的一元一次方程"]),
    "C002": ("等式性质", "掌握等式两边同时加、减、乘、除同一个非零数或式子后等式仍成立的性质。", ["只处理等式一边", "除以含未知数的式子时忽略非零条件", "去括号后没有保持等式平衡"], ["每次变形前说明两边做了什么操作", "特别关注乘除变形中的非零条件", "用天平模型理解等式平衡"]),
    "C003": ("代数运算", "掌握合并同类项、去括号、因式分解和代入求值等基本代数处理方法。", ["同类项判断错误", "负号处理错误", "因式分解不完整"], ["先标出同类项再合并", "遇到负号和括号时放慢一步", "整理常见因式分解公式"]),
    "C004": ("三角形面积", "掌握三角形面积公式 S = 底 × 高 ÷ 2，并能准确识别底和对应高。", ["忘记除以 2", "底和高不对应", "面积单位书写不完整"], ["计算前先写公式", "画图标出底和对应高", "注意面积单位是平方单位"]),
    "C005": ("一元二次方程", "理解一元二次方程的标准形式，能够用因式分解、配方法或公式法求解。", ["因式分解错误", "漏写一个根", "没有把方程化为标准形式"], ["先整理为 ax^2 + bx + c = 0", "优先观察能否因式分解", "求出两个根后代入验证"]),
    "C006": ("函数图像", "理解函数解析式、点坐标和图像之间的对应关系，能够通过代入、描点和读图解决问题。", ["混淆 x 和 y 坐标", "代入后计算错误", "不理解点在图像上的含义"], ["明确点 (x, y) 中每个数的位置", "把给定 x 代入解析式求 y", "结合表格和图像理解函数关系"]),
    "C007": ("分式运算", "掌握分式约分、通分、乘除和加减运算，并注意分母不为零的限制条件。", ["约分时跨项约分", "忽略分母不为零", "因式分解后漏项"], ["先因式分解再约分", "写出变量取值限制", "区分整体因式和单项式"]),
    "C008": ("几何证明", "能够根据条件选择合适的判定方法，组织严谨的几何证明步骤。", ["只写结论缺少理由", "辅助线选择不明确", "全等条件不完整"], ["按已知、求证、证明三部分书写", "补齐每一步的依据", "多练等腰三角形和全等三角形证明"]),
    "C009": ("统计图表", "能够读取条形图、折线图、扇形图和频数表，提取数据并进行比较。", ["读错纵轴单位", "忽略总量变化", "把频数和频率混淆"], ["先看图表标题和单位", "标出关键数据再计算", "区分数量、比例和变化趋势"]),
    "C010": ("概率初步", "理解随机事件、概率意义和简单等可能事件概率计算。", ["样本总数数错", "把不等可能事件当成等可能", "漏算有利情况"], ["列出所有可能结果", "先判断是否等可能", "用有利情况数除以总情况数"]),
    "C011": ("相似三角形", "掌握相似三角形判定、对应边比例和相似在测量问题中的应用。", ["对应边找错", "比例式方向写反", "判定条件不完整"], ["先标对应角和对应边", "写比例式前统一顺序", "判定后再使用相似性质"]),
    "C012": ("圆的性质", "理解圆心角、圆周角、切线和弦相关性质，能用于简单计算与证明。", ["混淆圆心角和圆周角", "忘记切线垂直半径", "弦、弧、角关系对应错误"], ["画图标出圆心和半径", "区分圆心角与圆周角位置", "证明题中写清使用的圆性质"]),
}


QUESTIONS = [
    ("Q001", "解方程：2x + 3 = 11。", "x=4", "easy", ["C001", "C002"], ["x=7", "x=5", "x=3"]),
    ("Q002", "化简：3a + 2a - 5。", "5a-5", "easy", ["C003"], ["6a-5", "5a+5", "a-5"]),
    ("Q003", "一个三角形底为 8 cm，高为 5 cm，求面积。", "20 平方厘米", "easy", ["C004"], ["40 平方厘米", "13 平方厘米", "20 厘米"]),
    ("Q004", "解方程：x^2 - 5x + 6 = 0。", "x=2 或 x=3", "medium", ["C005", "C003"], ["x=1 或 x=6", "x=2", "不会"]),
    ("Q005", "一次函数 y = 2x - 1 的图像经过点 (1, y)，求 y。", "1", "medium", ["C006", "C003"], ["3", "-1", "2"]),
    ("Q006", "计算：(x^2 - 1) / (x - 1)，其中 x 不等于 1。", "x+1", "medium", ["C007", "C003"], ["x-1", "x^2+1", "1"]),
    ("Q007", "已知三角形两边相等，证明其底角相等。", "作顶角平分线，可证明两个三角形全等，从而底角相等。", "hard", ["C008"], ["因为两边相等所以角相等", "两角相等", "证明过程不完整"]),
    ("Q008", "若 3(x - 2) = 12，求 x。", "x=6", "easy", ["C001", "C002", "C003"], ["x=2", "x=4", "x=8"]),
    ("Q009", "解方程：5 - 2x = 13。", "x=-4", "easy", ["C001", "C002"], ["x=4", "x=-9", "x=9"]),
    ("Q010", "化简：2(3x - 4) - x。", "5x-8", "easy", ["C003"], ["6x-8", "5x+8", "5x-4"]),
    ("Q011", "一个梯形上底 4 cm，下底 10 cm，高 6 cm，求面积。", "42 平方厘米", "medium", ["C004", "C003"], ["84 平方厘米", "60 平方厘米", "42 厘米"]),
    ("Q012", "解方程：x^2 - 9 = 0。", "x=3 或 x=-3", "medium", ["C005"], ["x=3", "x=-9 或 x=9", "x=0"]),
    ("Q013", "函数 y = -x + 4 中，当 x = 6 时，求 y。", "-2", "easy", ["C006", "C003"], ["2", "10", "-10"]),
    ("Q014", "化简：(2x)/(4x^2)，其中 x 不等于 0。", "1/(2x)", "medium", ["C007"], ["1/2", "2x", "1/(4x)"]),
    ("Q015", "已知两个三角形有两角分别相等，说明这两个三角形是否相似。", "相似", "medium", ["C011", "C008"], ["全等", "不一定相似", "无法判断"]),
    ("Q016", "袋中有 3 个红球、2 个白球，随机摸出 1 个球，摸到红球的概率是多少？", "3/5", "easy", ["C010"], ["2/5", "3/2", "1/3"]),
    ("Q017", "某班 40 人中 12 人喜欢篮球，求喜欢篮球人数所占比例。", "30%", "easy", ["C009", "C003"], ["12%", "40%", "3%"]),
    ("Q018", "圆中同弧所对的圆周角有什么关系？", "相等", "medium", ["C012"], ["互补", "相加等于圆心角", "不确定"]),
    ("Q019", "解方程：4(x + 1) = 2x + 10。", "x=3", "medium", ["C001", "C002", "C003"], ["x=2", "x=7", "x=-3"]),
    ("Q020", "若 a:b = 2:3，且 b = 12，求 a。", "8", "medium", ["C003", "C011"], ["18", "6", "10"]),
    ("Q021", "阅读折线图可知某日气温从 8 点到 12 点由 18℃ 升至 26℃，求升高了多少。", "8℃", "easy", ["C009"], ["44℃", "6℃", "10℃"]),
    ("Q022", "掷一枚均匀骰子，点数大于 4 的概率是多少？", "1/3", "easy", ["C010"], ["2/3", "1/6", "1/2"]),
    ("Q023", "已知相似三角形对应边比为 2:5，小三角形一边为 6，求大三角形对应边。", "15", "medium", ["C011", "C003"], ["12", "30", "2.4"]),
    ("Q024", "圆的切线与过切点的半径有什么位置关系？", "垂直", "easy", ["C012"], ["平行", "相交但不垂直", "重合"]),
    ("Q025", "解方程组：x + y = 7，x - y = 1，求 x。", "x=4", "medium", ["C001", "C002", "C003"], ["x=3", "x=6", "x=8"]),
    ("Q026", "因式分解：x^2 + 5x + 6。", "(x+2)(x+3)", "medium", ["C005", "C003"], ["(x+1)(x+6)", "(x-2)(x-3)", "不能分解"]),
    ("Q027", "一次函数 y = 3x + b 经过点 (2, 7)，求 b。", "1", "medium", ["C006", "C001", "C003"], ["13", "-1", "7"]),
    ("Q028", "计算：1/2 + 1/3。", "5/6", "easy", ["C007"], ["2/5", "1/5", "2/6"]),
    ("Q029", "证明平行四边形对角线互相平分，需要先连接哪两个顶点形成三角形证明？", "连接一条对角线", "hard", ["C008"], ["连接任意一边", "不用辅助线", "只看图即可"]),
    ("Q030", "某组数据 6, 8, 10, 10, 12 的众数是多少？", "10", "easy", ["C009"], ["9.2", "12", "6"]),
    ("Q031", "从数字 1,2,3,4 中随机选一个偶数的概率是多少？", "1/2", "easy", ["C010"], ["1/4", "2", "3/4"]),
    ("Q032", "同圆中半径为 5，直径是多少？", "10", "easy", ["C012"], ["5", "25", "2.5"]),
]


STUDENTS = [
    ("S001", "张明", "局部薄弱型", {"C004": 0.25, "C006": 0.35, "C008": 0.30}),
    ("S002", "李华", "全面掌握型", {}),
    ("S003", "王芳", "方程与综合薄弱型", {"C001": 0.35, "C002": 0.35, "C005": 0.30, "C007": 0.35, "C008": 0.30}),
    ("S004", "赵强", "证明薄弱型", {"C008": 0.25, "C011": 0.45, "C012": 0.45}),
    ("S005", "陈晨", "多知识点风险型", {"C001": 0.30, "C002": 0.35, "C003": 0.35, "C005": 0.30, "C006": 0.35, "C008": 0.25}),
    ("S006", "周雨欣", "代数薄弱型", {"C003": 0.35, "C005": 0.40, "C007": 0.45}),
    ("S007", "吴浩", "函数薄弱型", {"C006": 0.25, "C003": 0.55}),
    ("S008", "郑可", "统计概率薄弱型", {"C009": 0.35, "C010": 0.30}),
    ("S009", "孙悦", "几何综合薄弱型", {"C008": 0.35, "C011": 0.30, "C012": 0.35}),
    ("S010", "马宇航", "稳定中等型", {"C005": 0.55, "C008": 0.55}),
    ("S011", "林嘉怡", "全面掌握型", {}),
    ("S012", "何俊", "方程薄弱型", {"C001": 0.35, "C002": 0.40}),
    ("S013", "高蕾", "分式薄弱型", {"C007": 0.25, "C003": 0.50}),
    ("S014", "许诺", "概率薄弱型", {"C010": 0.25}),
    ("S015", "唐一鸣", "统计薄弱型", {"C009": 0.25}),
    ("S016", "曹欣然", "相似薄弱型", {"C011": 0.25, "C008": 0.50}),
    ("S017", "冯子涵", "圆薄弱型", {"C012": 0.25, "C008": 0.55}),
    ("S018", "梁晨", "代数函数薄弱型", {"C003": 0.40, "C006": 0.35}),
    ("S019", "宋佳琪", "基础不稳型", {"C001": 0.45, "C002": 0.45, "C003": 0.45, "C004": 0.45}),
    ("S020", "韩硕", "综合风险型", {"C001": 0.35, "C003": 0.35, "C005": 0.35, "C006": 0.35, "C008": 0.30, "C011": 0.35}),
    ("S021", "蒋依依", "全面掌握型", {}),
    ("S022", "罗天宇", "中等偏上型", {"C008": 0.55}),
    ("S023", "邓诗雨", "几何证明薄弱型", {"C008": 0.25, "C012": 0.45}),
    ("S024", "彭越", "统计概率薄弱型", {"C009": 0.40, "C010": 0.40}),
    ("S025", "乔安", "函数方程薄弱型", {"C006": 0.35, "C001": 0.45}),
    ("S026", "余嘉", "分式代数薄弱型", {"C007": 0.30, "C003": 0.40}),
    ("S027", "杜若", "面积薄弱型", {"C004": 0.25}),
    ("S028", "叶航", "二次方程薄弱型", {"C005": 0.25, "C003": 0.50}),
    ("S029", "沈青", "圆相似薄弱型", {"C011": 0.35, "C012": 0.30}),
    ("S030", "熊博", "多知识点风险型", {"C001": 0.35, "C002": 0.35, "C006": 0.35, "C009": 0.35, "C010": 0.35}),
    ("S031", "魏思源", "全面掌握型", {}),
    ("S032", "邹静", "稳定中等型", {"C004": 0.55, "C007": 0.55, "C012": 0.55}),
    ("S033", "田昊", "几何综合薄弱型", {"C004": 0.45, "C008": 0.35, "C011": 0.35, "C012": 0.35}),
    ("S034", "陆瑶", "代数薄弱型", {"C003": 0.30, "C005": 0.35}),
    ("S035", "白宁", "概率统计薄弱型", {"C009": 0.30, "C010": 0.25}),
    ("S036", "顾晨曦", "函数薄弱型", {"C006": 0.25}),
    ("S037", "任泽", "全面掌握型", {}),
    ("S038", "姚璐", "基础不稳型", {"C001": 0.45, "C002": 0.45, "C003": 0.45}),
    ("S039", "邵洋", "综合风险型", {"C003": 0.35, "C005": 0.35, "C007": 0.35, "C008": 0.35, "C011": 0.35}),
    ("S040", "程雪", "中等偏上型", {"C010": 0.55, "C012": 0.55}),
]


FIXED_RESULTS = {
    ("S001", "Q001"): 1, ("S001", "Q002"): 0, ("S001", "Q003"): 0, ("S001", "Q004"): 1,
    ("S001", "Q005"): 0, ("S001", "Q006"): 1, ("S001", "Q007"): 0, ("S001", "Q008"): 1,
    ("S002", "Q001"): 1, ("S002", "Q002"): 1, ("S002", "Q003"): 1, ("S002", "Q004"): 1,
    ("S002", "Q005"): 1, ("S002", "Q006"): 1, ("S002", "Q007"): 1, ("S002", "Q008"): 1,
    ("S003", "Q001"): 0, ("S003", "Q002"): 1, ("S003", "Q003"): 1, ("S003", "Q004"): 0,
    ("S003", "Q005"): 1, ("S003", "Q006"): 0, ("S003", "Q007"): 0, ("S003", "Q008"): 0,
    ("S004", "Q001"): 1, ("S004", "Q002"): 1, ("S004", "Q003"): 1, ("S004", "Q004"): 1,
    ("S004", "Q005"): 1, ("S004", "Q006"): 1, ("S004", "Q007"): 0, ("S004", "Q008"): 1,
    ("S005", "Q001"): 0, ("S005", "Q002"): 0, ("S005", "Q003"): 1, ("S005", "Q004"): 0,
    ("S005", "Q005"): 0, ("S005", "Q006"): 1, ("S005", "Q007"): 0, ("S005", "Q008"): 1,
}


def main() -> None:
    random.seed(RANDOM_SEED)
    knowledge_base = {
        concept_id: {
            "concept_id": concept_id,
            "concept_name": item[0],
            "description": item[1],
            "common_errors": item[2],
            "learning_suggestions": item[3],
        }
        for concept_id, item in CONCEPTS.items()
    }
    questions = [
        {
            "question_id": question_id,
            "content": content,
            "correct_answer": answer,
            "difficulty": difficulty,
            "concept_ids": concept_ids,
            "knowledge_points": concept_ids,
            "wrong_answer_examples": wrongs,
        }
        for question_id, content, answer, difficulty, concept_ids, wrongs in QUESTIONS
    ]
    responses = _build_responses(questions)
    profiles = {
        student_id: {
            "student_id": student_id,
            "student_name": student_name,
            "profile_type": profile_type,
            "expected_weak_concepts": list(profile.keys()),
        }
        for student_id, student_name, profile_type, profile in STUDENTS
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "knowledge_base.json").write_text(
        json.dumps(knowledge_base, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DATA_DIR / "questions.json").write_text(
        json.dumps(questions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DATA_DIR / "student_profiles.json").write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_q_matrix(questions)
    _write_responses(responses)
    print(
        json.dumps(
            {
                "concepts": len(CONCEPTS),
                "questions": len(QUESTIONS),
                "students": len(STUDENTS),
                "responses": len(responses),
            },
            ensure_ascii=False,
        )
    )


def _build_responses(questions: list[dict]) -> list[dict]:
    responses = []
    for student_id, student_name, _, profile in STUDENTS:
        for question in questions:
            question_id = question["question_id"]
            if (student_id, question_id) in FIXED_RESULTS:
                is_correct = FIXED_RESULTS[(student_id, question_id)]
            else:
                probability = _correct_probability(profile, question["concept_ids"], question["difficulty"])
                is_correct = int(random.random() < probability)
            answer = question["correct_answer"] if is_correct else random.choice(question["wrong_answer_examples"])
            responses.append(
                {
                    "student_id": student_id,
                    "student_name": student_name,
                    "question_id": question_id,
                    "student_answer": answer,
                    "is_correct": is_correct,
                    "score": float(is_correct),
                }
            )
    return responses


def _correct_probability(profile: dict[str, float], concept_ids: list[str], difficulty: str) -> float:
    difficulty_adjust = {"easy": 0.10, "medium": -0.04, "hard": -0.14}
    required = [profile.get(concept_id, random.choice([0.72, 0.78, 0.84, 0.90, 0.94])) for concept_id in concept_ids]
    probability = min(required) + difficulty_adjust[difficulty]
    if len(concept_ids) >= 3:
        probability -= 0.06
    elif len(concept_ids) == 2:
        probability -= 0.03
    return max(0.08, min(0.96, probability))


def _write_q_matrix(questions: list[dict]) -> None:
    concept_ids = list(CONCEPTS.keys())
    with (DATA_DIR / "q_matrix.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["question_id"] + concept_ids)
        for question in questions:
            writer.writerow(
                [question["question_id"]]
                + [1 if concept_id in question["concept_ids"] else 0 for concept_id in concept_ids]
            )


def _write_responses(responses: list[dict]) -> None:
    with (DATA_DIR / "responses.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["student_id", "student_name", "question_id", "student_answer", "is_correct", "score"],
        )
        writer.writeheader()
        writer.writerows(responses)


if __name__ == "__main__":
    main()
