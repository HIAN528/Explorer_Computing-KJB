"""
공평성 점수 계산 (API 호출 없음)

입력 times: 소요시간 표 (행 = 후보역, 열 = 참여자, 값 = 분)

역마다 세 가지 지표를 구한다.
  - 총합: 모두의 이동시간 합      → 작을수록 전체가 덜 움직인다 (효율)
  - 최장: 가장 오래 걸리는 사람의 시간 → 작을수록 가장 먼 사람을 배려한다
  - 편차: 이동시간의 표준편차(ddof=0) → 작을수록 다들 비슷하게 걸린다 (균등)

세 지표는 단위와 크기가 달라 그대로 더할 수 없으므로,
각각 0~1로 min-max 정규화한 뒤 가중치를 곱해 더한다. 점수는 낮을수록 좋다.
"""

import pandas as pd

# 기준 이름 → (총합, 최장, 편차) 가중치
PRESETS = {
    "효율형": (1, 0, 0),
    "배려형": (0, 1, 0),
    "균등형": (0, 0, 1),
}

PRESET_DESCRIPTIONS = {
    "효율형": "모두의 이동시간 합이 가장 작은 곳. 전체적으로 덜 움직인다.",
    "배려형": "가장 오래 걸리는 사람의 시간이 가장 짧은 곳. 제일 먼 사람을 배려한다.",
    "균등형": "이동시간이 서로 가장 비슷한 곳. 누구 하나 손해 보지 않는다.",
    "맞춤형": "세 지표의 중요도를 슬라이더로 직접 정한다.",
}


def summarize(times):
    """역별 총합·최장·편차를 계산한 표를 돌려준다."""
    summary = pd.DataFrame(index=times.index)
    summary["총합"] = times.sum(axis=1)
    summary["최장"] = times.max(axis=1)
    summary["편차"] = times.std(axis=1, ddof=0)  # ddof=0: 모집단 표준편차
    return summary


def normalize(values):
    """min-max 정규화: 가장 작은 값 → 0, 가장 큰 값 → 1.

    모든 값이 같으면 (최댓값 = 최솟값) 0으로 나누게 되므로 전부 0으로 둔다.
    """
    low = values.min()
    high = values.max()
    if high == low:
        return values * 0.0
    return (values - low) / (high - low)


def score_stations(times, weights):
    """가중치로 공평성 점수를 매기고 점수가 낮은(좋은) 순으로 정렬한다.

    weights: (총합 가중치, 최장 가중치, 편차 가중치)
    반환: 총합·최장·편차·점수·순위 열이 있는 DataFrame.
          가중치 합이 0이면 계산할 수 없으므로 None.
    """
    w_total, w_max, w_std = weights
    weight_sum = w_total + w_max + w_std
    if weight_sum == 0:
        return None

    summary = summarize(times)
    weighted = (
        w_total * normalize(summary["총합"])
        + w_max * normalize(summary["최장"])
        + w_std * normalize(summary["편차"])
    )
    # 가중치 합으로 나눠서 점수도 0~1 범위가 되게 한다
    summary["점수"] = weighted / weight_sum

    # 점수가 같으면 최장 → 총합이 작은 역을 앞에 둔다
    summary = summary.sort_values(["점수", "최장", "총합"])
    summary["순위"] = range(1, len(summary) + 1)
    return summary


def best_by_preset(times):
    """프리셋 기준(효율형·배려형·균등형)마다 1위 역을 구한다.

    반환: {"효율형": "역 이름", ...}
    """
    result = {}
    for preset_name, weights in PRESETS.items():
        ranking = score_stations(times, weights)
        result[preset_name] = ranking.index[0]
    return result


# ---------------- 동작 확인: python -m utils.fairness ----------------
if __name__ == "__main__":
    # 기준에 따라 1위가 달라지도록 만든 예시 표 (단위: 분)
    times = pd.DataFrame(
        {"민수": [10, 25, 35], "지수": [10, 25, 35], "철수": [60, 33, 35]},
        index=["가역", "나역", "다역"],
    )
    print(times, "\n")
    print(summarize(times).round(1), "\n")
    # 가역: 총합 80(최소) / 나역: 최장 33(최소) / 다역: 편차 0(최소)

    best = best_by_preset(times)
    print("기준별 1위:", best)
    assert best["효율형"] == "가역"
    assert best["배려형"] == "나역"
    assert best["균등형"] == "다역"

    print("\n맞춤형 (1, 1, 0):")
    print(score_stations(times, (1, 1, 0)).round(2))

    assert score_stations(times, (0, 0, 0)) is None  # 가중치 합 0
    same = pd.Series([5, 5, 5])
    assert list(normalize(same)) == [0.0, 0.0, 0.0]  # 모두 같은 값
    print("\nfairness.py 확인 완료")
