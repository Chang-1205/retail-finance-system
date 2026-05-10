import argparse
import random
import time
import requests

DEFAULT_URL = "http://localhost:8000/api/webhook/transaction"

PLATFORMS = [
    {"name": "Shopee", "payment_method_id": 1, "channel_id": 2},
    {"name": "Momo", "payment_method_id": 2, "channel_id": 3},
]

STORE_IDS = [1, 2, 3]


def build_payload(platform_name: str, order_id: str, amount: float, store_id: int, channel_id: int, payment_method_id: int) -> dict:
    return {
        "platform": platform_name,
        "order_id": order_id,
        "amount": amount,
        "store_id": store_id,
        "channel_id": channel_id,
        "payment_method_id": payment_method_id,
        "note": "Đơn hàng giả lập từ bot webhook"
    }


def generate_order_id(platform_name: str) -> str:
    prefix = platform_name[:3].upper()
    return f"{prefix}-{random.randint(100000, 999999)}"


def main(api_url: str, interval: int):
    print(f"Bắt đầu Mock Webhook Bot, gửi dữ liệu mỗi {interval} giây đến: {api_url}")
    while True:
        platform = random.choice(PLATFORMS)
        amount = random.randint(100000, 500000)
        payload = build_payload(
            platform_name=platform["name"],
            order_id=generate_order_id(platform["name"]),
            amount=amount,
            store_id=random.choice(STORE_IDS),
            channel_id=platform["channel_id"],
            payment_method_id=platform["payment_method_id"],
        )

        try:
            response = requests.post(api_url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(f"✔ Đã gửi {payload['platform']} order {payload['order_id']} - {payload['amount']} VND => id: {data.get('id')}")
        except Exception as ex:
            print(f"✖ Lỗi gửi webhook: {ex}")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Webhook Bot cho Shopee/Momo gửi dữ liệu doanh thu vào backend.")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL endpoint webhook của backend")
    parser.add_argument("--interval", type=int, default=5, help="Khoảng cách gửi webhook theo giây")
    args = parser.parse_args()
    main(args.url, args.interval)
