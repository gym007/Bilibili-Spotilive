import datetime

def timestamp():
    # 生成当前时间的字符串，格式： [YYYY-MM-DD HH:MM:SS,fff]
    now = datetime.datetime.now()
    # %f 返回微秒（6位），取前三位表示毫秒，然后拼接在时间后面
    return now.strftime("[%Y-%m-%d %H:%M:%S,") + f"{now.microsecond // 1000:03d}]"