// 仅供测试子进程：阻止任何真实网络调用，按序返回固定 JSON。
const replies = JSON.parse(process.env.SKILL_MOCK_REPLIES);
globalThis.fetch = async () => {
  if (!replies.length) throw new Error('模拟响应已耗尽，不允许真实网络');
  return new Response(JSON.stringify(replies.shift()));
};
