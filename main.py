export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 회원가입 처리
    if (request.method === "POST" && url.pathname === "/api/signup") {
      const { id, pw } = await request.json();
      await env.USERS.put(id, pw);
      return new Response(JSON.stringify({ msg: "가입 성공!" }));
    }

    // 로그인 처리
    if (request.method === "POST" && url.pathname === "/api/login") {
      const { id, pw } = await request.json();
      const storedPw = await env.USERS.get(id);
      if (storedPw === pw) return new Response(JSON.stringify({ success: true, msg: "환영합니다!" }));
      return new Response(JSON.stringify({ success: false, msg: "정보가 틀립니다." }), { status: 401 });
    }

    // HTML 출력 (위의 HTML 코드를 여기에 붙여넣으세요)
    return new Response(`[위의 HTML 코드 붙여넣기]`, {
      headers: { "Content-Type": "text/html; charset=utf-8" }
    });
  }
};
