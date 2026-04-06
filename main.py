# 주문 ID 생성 변경
# 기존
order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

# 변경 - 4x4x6 형식
def generate_order_id():
    p1 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    p2 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    p3 = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{p1}-{p2}-{p3}"
