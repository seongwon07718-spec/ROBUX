const { Client, GatewayIntentBits, Partials, InteractionType, ModalBuilder, TextInputBuilder, TextInputStyle, ActionRowBuilder } = require("discord.js");
const { fetch } = require("undici");

// 환경변수 읽기
const TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const GUILD_ID = process.env.GUILD_ID || "1419200424636055592";

// 필수값 체크
if (!TOKEN) {
  console.error("DISCORD_TOKEN 비어있음");
  process.exit(1);
}
if (!CHANNEL_ID) {
  console.error("CHANNEL_ID 비어있음(텍스트 채널 ID)");
  process.exit(1);
}

// 클라이언트 생성
const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
  partials: [Partials.Channel],
});

// 유저별 선택값 캐시
const userSelected = new Map();

// 카드 느낌 본문(임베드 X)
function makeContentLikeCard(selected) {
  let top =
    "┌─────────────────────────────────\n" +
    "│ 테스트입니다.\n" +
    "│ JS로 Components 느낌 살려서 구현.\n" +
    "│ 임베드 없이 컴포넌트로만 구성.\n" +
    "└─────────────────────────────────";
  if (selected) top += `\n선택한 상품: ${selected}`;
  return top;
}

// 호환 컴포넌트(숫자 타입)
function makeComponentsLikeCard() {
  return [
    {
      type: 1, // Action Row
      components: [
        {
          type: 3, // String Select
          custom_id: "shop:select",
          placeholder: "상품을 선택해줘",
          min_values: 1,
          max_values: 1,
          options: [
            { label: "Robux 100", value: "rbx100", description: "100 크레딧" },
            { label: "Robux 500", value: "rbx500", description: "500 크레딧" },
            { label: "Robux 1000", value: "rbx1k", description: "1000 크레딧" },
          ],
        },
      ],
    },
    {
      type: 1,
      components: [
        { type: 2, style: 3, label: "구매", custom_id: "shop:buy" },       // SUCCESS
        { type: 2, style: 2, label: "자세히", custom_id: "shop:details" }, // SECONDARY
      ],
    },
  ];
}

// 채널 검증
async function validateChannel(channelId) {
  try {
    const ch = await client.channels.fetch(channelId);
    // GuildText = 0
    if (!ch || ch.type !== 0) return [false, "텍스트 채널이 아님."];
    if (String(ch.guildId) !== String(GUILD_ID)) return [false, `길드 불일치(${ch.guildId} != ${GUILD_ID})`];
    const me = await ch.guild.members.fetchMe();
    const perms = ch.permissionsFor(me);
    if (!perms?.has("SendMessages")) return [false, "메시지 보내기 권한 없음."];
    return [true, "OK"];
  } catch (e) {
    return [false, `채널 조회 실패: ${e?.message || e}`];
  }
}

client.once("ready", async () => {
  console.log(`READY ${client.user.tag} | guild=${GUILD_ID} | channel=${CHANNEL_ID}`);

  const [ok, reason] = await validateChannel(CHANNEL_ID);
  if (!ok) {
    console.log(`[차단] 전송 중단: ${reason}`);
    return;
  }

  // 원시 REST로 메시지 전송
  const url = `https://discord.com/api/v10/channels/${CHANNEL_ID}/messages`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bot ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      content: makeContentLikeCard(),
      components: makeComponentsLikeCard(),
      allowed_mentions: { parse: [] },
    }),
  });

  const text = await res.text();
  console.log("send:", res.status, text);
  if (res.status >= 300) console.log("전송 실패. 위 body 참고.");
});

// 인터랙션 처리
client.on("interactionCreate", async (interaction) => {
  // 셀렉트
  if (interaction.isStringSelectMenu() && interaction.customId === "shop:select") {
    const sku = interaction.values?.[0];
    if (!sku) {
      await interaction.reply({ content: "선택값 없음. 다시 시도!", ephemeral: true });
      return;
    }
    userSelected.set(interaction.user.id, sku);
    await interaction.update({
      content: makeContentLikeCard(sku),
      components: makeComponentsLikeCard(),
    });
    return;
  }

  // 구매 버튼
  if (interaction.isButton() && interaction.customId === "shop:buy") {
    const sku = userSelected.get(interaction.user.id);
    if (!sku) {
      await interaction.reply({ content: "먼저 상품을 선택해줘!", ephemeral: true });
      return;
    }
    const modal = new ModalBuilder().setCustomId(`qty:${sku}`).setTitle("구매 수량 입력");

    const qty = new TextInputBuilder()
      .setCustomId("qty")
      .setLabel("수량")
      .setPlaceholder("1 이상 정수")
      .setMinLength(1)
      .setMaxLength(6)
      .setRequired(true)
      .setStyle(TextInputStyle.Short);

    modal.addComponents(new ActionRowBuilder().addComponents(qty));
    await interaction.showModal(modal);
    return;
  }

  // 모달 제출
  if (interaction.type === InteractionType.ModalSubmit && interaction.customId.startsWith("qty:")) {
    const sku = interaction.customId.split(":")[1];
    const qty = interaction.fields.getTextInputValue("qty");
    const val = parseInt(String(qty).trim(), 10);
    if (!Number.isInteger(val) || val <= 0) {
      await interaction.reply({ content: "수량이 올바르지 않아. 1 이상 정수!", ephemeral: true });
      return;
    }
    const orderId = `ord-${sku}-${val}`;
    await interaction.reply({ content: `주문 완료! SKU: ${sku}, 수량: ${val}\n주문번호: ${orderId}`, ephemeral: true });
    return;
  }

  // 자세히 버튼
  if (interaction.isButton() && interaction.customId === "shop:details") {
    await interaction.reply({ content: "자세한 가이드는 곧 연결!", ephemeral: true });
  }
});

// 로그인
client.login(TOKEN);
