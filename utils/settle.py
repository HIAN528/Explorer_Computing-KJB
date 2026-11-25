"""
정산 알고리즘 (그리디 방식)

1. 1인당 부담액 = 총액 / 인원
2. 사람별 잔액 = 낸 돈 - 1인당 부담액
     잔액 > 0 → 받을 사람, 잔액 < 0 → 보낼 사람
3. 가장 많이 보내야 하는 사람과 가장 많이 받아야 하는 사람을 짝지어
   둘 중 작은 금액만큼 송금한다. 한쪽이 0이 되면 다음 사람으로 넘어간다.
   이렇게 하면 송금 횟수가 최대 (인원 - 1)번으로 줄어든다.
"""


def calc_balances(names, paid):
    """사람별 잔액(낸 돈 - 1인당 부담액)을 dict로 돌려준다. (+ 받을 돈 / − 낼 돈)"""
    share = sum(paid) / len(names)
    balances = {}
    for name, amount in zip(names, paid):
        balances[name] = amount - share
    return balances


def settle(names, paid):
    """누가 누구에게 얼마를 보내면 되는지 계산한다.

    names: 이름 목록, paid: 각자 낸 금액 목록 (같은 순서)
    반환: (송금 목록, 잔액 dict)
      송금 목록: [{"from": "민수", "to": "지수", "amount": 15000}, ...]
      잔액 dict: {"민수": -15000, "지수": 15000, ...} (원 단위 반올림)
    """
    if len(names) == 0:
        return [], {}

    balances = calc_balances(names, paid)

    # [이름, 남은 금액] 목록을 금액이 큰 순으로 정렬
    senders = [[name, -bal] for name, bal in balances.items() if bal < 0]
    receivers = [[name, bal] for name, bal in balances.items() if bal > 0]
    senders.sort(key=lambda x: x[1], reverse=True)
    receivers.sort(key=lambda x: x[1], reverse=True)

    transfers = []
    i = 0  # 지금 보낼 사람 번호
    j = 0  # 지금 받을 사람 번호
    while i < len(senders) and j < len(receivers):
        amount = min(senders[i][1], receivers[j][1])
        if round(amount) > 0:
            transfers.append({"from": senders[i][0], "to": receivers[j][0], "amount": round(amount)})
        senders[i][1] -= amount
        receivers[j][1] -= amount
        # 1원 미만이 남으면 끝난 것으로 본다 (나누어떨어지지 않을 때 생기는 자투리)
        if senders[i][1] < 1:
            i += 1
        if receivers[j][1] < 1:
            j += 1

    rounded = {name: round(bal) for name, bal in balances.items()}
    return transfers, rounded


# ---------------- 동작 확인: python -m utils.settle ----------------
if __name__ == "__main__":
    names = ["민수", "지수", "철수", "영희"]
    paid = [60000, 0, 20000, 0]  # 총 80,000원 → 1인당 20,000원
    transfers, balances = settle(names, paid)
    print("잔액:", balances)
    for t in transfers:
        print(f"{t['from']} → {t['to']} {t['amount']:,}원")
    assert balances == {"민수": 40000, "지수": -20000, "철수": 0, "영희": -20000}
    assert len(transfers) == 2
    assert sum(t["amount"] for t in transfers) == 40000

    # 나누어떨어지지 않는 경우: 10,000원 / 3명
    transfers, balances = settle(["A", "B", "C"], [10000, 0, 0])
    print("\n잔액:", balances)
    for t in transfers:
        print(f"{t['from']} → {t['to']} {t['amount']:,}원")
    assert len(transfers) == 2

    # 모두 똑같이 낸 경우 → 송금 없음
    transfers, _ = settle(["A", "B"], [5000, 5000])
    assert transfers == []

    assert settle([], []) == ([], {})
    print("\nsettle.py 확인 완료")
