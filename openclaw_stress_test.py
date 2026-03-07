import asyncio
import websockets
import json
import uuid
import random
import time
from datetime import datetime

# Gateway 配置
GATEWAY_URL = "ws://127.0.0.1:18789/chat"
AUTH_TOKEN = "xxx"
SESSION_ID = "agent:main:main"  # 使用默认 session 以便统计 tokens 指标

# 压力测试配置
RESET_CONTEXT_AFTER = 10  # 每 N 次请求后重置上下文
MIN_INTERVAL = 60  # 最小间隔秒数
MAX_INTERVAL = 120  # 最大间隔秒数
REQUEST_TIMEOUT = 120  # 请求超时时间

# 随机测试消息池
TEST_MESSAGES = [
    # 基础对话
    "你好，请简单介绍一下你自己",
    "给我讲个笑话",
    "1+1等于几？",

    # 天气相关
    "今天北京天气怎么样？",
    "明天上海会下雨吗？",
    "这周深圳天气预报",
    "广州现在气温多少度？",

    # 新闻资讯
    "今天有什么重要新闻？",
    "最近科技圈有什么大事？",
    "总结一下今天的热点新闻",
    "AI领域最近有什么进展？",

    # 触发 tech-news-digest skill 的问题
    "给我看看今天的科技新闻摘要",
    "帮我总结今天的科技新闻",
    "今日科技新闻汇总",
    "科技新闻摘要",
    "最新的科技新闻有哪些？",
    "今天科技圈发生了什么？",
    "tech news digest",
    "tech news summary",
    "今天的 tech news",
    "给我一份科技新闻简报",

    # 技术问题
    "帮我写一个Python的快速排序算法",
    "什么是机器学习？",
    "解释一下什么是RESTful API",
    "Docker和虚拟机有什么区别？",
    "如何学习编程？",
    "解释一下async和await的用法",
    "什么是微服务架构？",

    # 实用查询
    "OpenClaw是什么？",
    "推荐几本好看的科幻小说",
    "如何提高代码质量？",
    "推荐一些编程学习资源",
    "今天是几月几号？",
    "现在几点了？",

    # 任务类
    "帮我制定一个学习Python的计划",
    "总结一下人工智能的发展历史",
    "分析一下当前互联网行业趋势",

    # 触发上下文压缩的长请求
    "请详细介绍Python编程语言的发展历史、主要特性、应用场景、生态系统、以及在数据科学、Web开发、人工智能等领域的优势和劣势，并给出具体的代码示例和最佳实践建议",
    "请全面分析当前人工智能技术的发展现状，包括深度学习、强化学习、自然语言处理、计算机视觉等各个领域的最新进展，主要的开源框架和工具，典型应用案例，以及未来发展趋势和面临的挑战",
    "请详细说明如何从零开始搭建一个完整的微服务架构系统，包括技术选型、架构设计、服务拆分、API网关、服务注册发现、配置中心、链路追踪、日志收集、监控告警等各个方面的实现方案和最佳实践",
    "请系统讲解现代前端开发的完整技术栈，包括React、Vue、Angular等框架的特点对比，Webpack、Vite等构建工具的使用，状态管理方案，TypeScript开发，性能优化技巧，测试方案，以及最新的前端工程化实践",
    "请深入分析分布式系统设计的核心概念和关键技术，包括CAP定理、分布式一致性算法（Raft、Paxos）、分布式事务处理、消息队列、缓存策略、数据分片、负载均衡等，并结合实际案例说明如何解决常见问题",
    "请详细介绍云原生技术体系，包括容器化（Docker）、容器编排（Kubernetes）、服务网格（Istio）、Serverless架构、CI/CD流水线、DevOps实践、监控可观测性等内容，以及如何在生产环境中落地应用",
    "请全面讲解数据库设计与优化的方法论，包括关系型数据库（MySQL、PostgreSQL）和NoSQL数据库（MongoDB、Redis、Elasticsearch）的选型原则、Schema设计、索引优化、查询优化、分库分表、读写分离等策略",
    "请系统性地介绍网络安全的各个层面，包括Web安全（XSS、CSRF、SQL注入等）、密码学基础、HTTPS原理、身份认证与授权（OAuth2.0、JWT）、安全审计、渗透测试、以及如何构建企业级安全防护体系",
    "请详细说明如何设计和实现一个高可用、高性能、可扩展的电商系统，包括系统架构、数据库设计、缓存方案、搜索引擎、订单处理、支付集成、库存管理、秒杀场景、以及性能压测和容量规划",
    "请深入探讨大数据处理技术栈，包括Hadoop生态（HDFS、MapReduce、Yarn）、Spark计算框架、Flink流处理、Kafka消息系统、数据仓库建设（Hive、Presto）、数据湖架构、以及实时数据分析的实现方案",

    # 文件操作测试
    "帮我创建一个文件 /home/yemo/test.txt，内容是 'Hello from OpenClaw stress test'",
    "请写入一些测试内容到 /home/yemo/test.txt",
    "在 /home/yemo/test.txt 文件中添加当前时间戳",
    "帮我在 /home/yemo/test.txt 中写入一段Python代码示例",
    "将'Stress test running'这段文字写入 /home/yemo/test.txt",

    # Shell 命令执行测试
    "帮我创建一个shell脚本 /home/yemo/t.sh，内容是打印当前日期和时间",
    "请执行脚本 /home/yemo/t.sh",
    "运行 /home/yemo/t.sh 并告诉我输出结果",
    "帮我在 /home/yemo/t.sh 中写入一个检查系统负载的命令",
    "执行 bash /home/yemo/t.sh"
]

# 统计数据
stats = {
    "total_requests": 0,
    "success_count": 0,
    "error_count": 0,
    "context_resets": 0,
    "start_time": None
}


def log(message):
    """带时间戳的日志输出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def print_stats():
    """打印统计信息"""
    if stats["start_time"]:
        elapsed = time.time() - stats["start_time"]
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)

        log("=" * 60)
        log(f"📊 统计信息")
        log(f"运行时间: {hours}小时 {minutes}分钟 {seconds}秒")
        log(f"总请求数: {stats['total_requests']}")
        log(f"成功: {stats['success_count']}")
        log(f"失败: {stats['error_count']}")
        log(f"上下文重置次数: {stats['context_resets']}")
        if stats['total_requests'] > 0:
            success_rate = (stats['success_count'] /
                            stats['total_requests']) * 100
            log(f"成功率: {success_rate:.2f}%")
        log("=" * 60)


async def send_message(websocket, message, session_id):
    """发送单个消息并接收响应"""
    req_id = str(uuid.uuid4())
    chat_req = {
        "type": "req",
        "id": req_id,
        "method": "agent",
        "params": {
            "message": message,
            "idempotencyKey": req_id,
            "sessionKey": session_id
        }
    }

    await websocket.send(json.dumps(chat_req))
    log(f"📤 发送消息 (Session: {session_id}): {message}")

    # 接收响应
    response_text = []
    while True:
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=REQUEST_TIMEOUT)
            resp_data = json.loads(response)

            msg_type = resp_data.get("type", "")
            event = resp_data.get("event", "")

            # 跳过 tick 和 health 事件
            if event in ["tick", "health"]:
                continue

            # 收集流式内容
            if event == "agent" and "data" in resp_data.get("payload", {}):
                data = resp_data["payload"]["data"]
                if "delta" in data:
                    response_text.append(data["delta"])
            elif event == "chat" and resp_data.get("payload", {}).get("state") == "final":
                full_text = "".join(response_text)
                log(f"📥 收到回复 (长度: {len(full_text)} 字符)")
                return True
            elif msg_type == "res" and resp_data.get("ok"):
                payload = resp_data.get("payload", {})
                if payload.get("status") == "ok":
                    full_text = "".join(response_text)
                    log(f"📥 收到回复 (长度: {len(full_text)} 字符)")
                    return True
        except asyncio.TimeoutError:
            log("⚠️ 请求超时")
            return False


async def connect_and_auth(session_id):
    """连接并认证"""
    uri = f"{GATEWAY_URL}?session={session_id}"
    websocket = await websockets.connect(uri)
    log(f"✅ 已连接到 Gateway")

    # 接收认证挑战
    challenge_msg = await websocket.recv()
    challenge = json.loads(challenge_msg)

    if challenge.get("type") == "event" and challenge.get("event") == "connect.challenge":
        # 发送 connect 请求
        connect_req = {
            "type": "req",
            "id": str(uuid.uuid4()),
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "cli",
                    "version": "1.0.0",
                    "platform": "linux",
                    "mode": "cli"
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write"],
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": {"token": AUTH_TOKEN},
                "locale": "zh-CN",
                "userAgent": "python-stress-test/2.0.0"
            }
        }
        await websocket.send(json.dumps(connect_req))

        # 等待 connect 响应
        connect_res = await websocket.recv()
        res_data = json.loads(connect_res)

        if res_data.get("ok"):
            log(f"🔐 认证成功")
            return websocket
        else:
            raise Exception(f"认证失败: {res_data}")
    else:
        raise Exception(f"未知响应: {challenge}")


async def stress_test_loop():
    """持续压力测试循环"""
    stats["start_time"] = time.time()
    log("🚀 压力测试启动")
    log(f"配置: 每 {RESET_CONTEXT_AFTER} 次请求重置上下文")
    log(f"请求间隔: {MIN_INTERVAL}-{MAX_INTERVAL} 秒随机")
    log(f"消息池大小: {len(TEST_MESSAGES)} 条")
    log(f"使用 Session: {SESSION_ID}")

    websocket = None
    request_count_in_session = 0

    try:
        while True:
            try:
                # 检查是否需要重置上下文（关闭连接，清空历史）
                if request_count_in_session >= RESET_CONTEXT_AFTER:
                    if websocket:
                        await websocket.close()

                    websocket = None
                    request_count_in_session = 0
                    stats["context_resets"] += 1
                    log(f"🔄 重置上下文 (第 {stats['context_resets']} 次) - 关闭连接重新开始")

                    # 等待一小段时间
                    await asyncio.sleep(2)

                # 建立连接 (如果需要)
                if not websocket:
                    websocket = await connect_and_auth(SESSION_ID)

                # 随机选择消息
                message = random.choice(TEST_MESSAGES)

                # 发送消息
                stats["total_requests"] += 1
                success = await send_message(websocket, message, SESSION_ID)

                if success:
                    stats["success_count"] += 1
                    request_count_in_session += 1
                else:
                    stats["error_count"] += 1

                # 每 10 次请求打印一次统计
                if stats["total_requests"] % 10 == 0:
                    print_stats()

                # 随机等待
                wait_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                log(f"⏳ 等待 {wait_time} 秒...")
                await asyncio.sleep(wait_time)

            except websockets.exceptions.ConnectionClosed:
                log("⚠️ 连接关闭，重新连接...")
                websocket = None
                stats["error_count"] += 1
                await asyncio.sleep(5)
            except Exception as e:
                log(f"❌ 错误: {e}")
                stats["error_count"] += 1
                await asyncio.sleep(5)

    except KeyboardInterrupt:
        log("\n⚠️ 收到中断信号，正在退出...")
        if websocket:
            await websocket.close()
        print_stats()
    finally:
        if websocket:
            await websocket.close()

if __name__ == "__main__":
    asyncio.run(stress_test_loop())
