import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import schedule
from dotenv import dotenv_values
from twikit import Client

config = dotenv_values(".env")
csv_file = "output.csv"

USERNAME = config.get("X_USERNAME")
EMAIL = config.get("X_EMAIL")
PASSWORD = config.get("X_PASSWORD")
WEBHOOK_URL = config.get("WEBHOOK_LARK")
TARGET_SCREEN_NAME = "gumi_oshi3_en"


def initialize_client():
    client = Client("ja")
    client.login(auth_info_1=USERNAME, auth_info_2=EMAIL, password=PASSWORD)
    client.save_cookies("cookies.pickle")
    return client


def get_client():
    client = Client("ja")
    client.load_cookies("cookies.pickle")
    return client


def count_user_followers(client):
    user = client.get_user_by_screen_name(TARGET_SCREEN_NAME)
    return user.followers_count


def csv_output(total_followers):
    local_timezone = timezone(timedelta(seconds=-time.timezone))
    local_time = datetime.now(local_timezone)
    data = {
        "時間": [local_time.strftime("%Y-%m-%d %H:%M:%S")],
        "総計": [total_followers],
    }
    df = pd.DataFrame(data)
    if not os.path.isfile(csv_file):
        df.to_csv(csv_file, index=False)
        print("新しいCSVファイルを作成しました。")
    else:
        df.to_csv(csv_file, mode="a", header=False, index=False)
        print(f"データがCSVファイルに追加されました: {csv_file}")


def update_message(total_followers):
    df = pd.read_csv(csv_file)
    last_total = df.iloc[-1]["総計"] if not df.empty else 0
    difference = total_followers - last_total
    message = f"現在OSHI3 X のフォロワー数は {total_followers} になりました。\n"
    if difference < 0:
        message += f"前回の総計から {difference} 減少した。"
    elif difference > 0:
        message += f"前回の総計から {difference} 増加した。"
    else:
        message += "前回の総計と変わりませんでした。"
    return message


def send_webhook(message):
    response = requests.post(
        WEBHOOK_URL,
        json={
            "msg_type": "text",
            "content": {"text": message},
        },
    )
    if response.status_code == 200:
        print("メッセージが正常に送信されました。")
    else:
        print(
            f"メッセージの送信に失敗しました。ステータスコード: {response.status_code}",
        )


if __name__ == "__main__":
    client = initialize_client()
    client = get_client()
    total_followers = count_user_followers(client)
    csv_output(total_followers)
    message = update_message(total_followers)
    send_webhook(message)

    schedule.every(30).minutes.do(lambda: csv_output(count_user_followers(client)))
    schedule.every(3).hours.do(
        lambda: send_webhook(update_message(count_user_followers(client))),
    )

    while True:
        schedule.run_pending()
        time.sleep(1)
