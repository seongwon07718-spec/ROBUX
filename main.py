'use strict';
require('dotenv/config');

const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  MessageFlags,
  ButtonBuilder,
  ButtonStyle,
  ActionRowBuilder,
} = require('discord.js');

const {
  ContainerBuilder,
  SectionBuilder,
  TextDisplayBuilder,
  SeparatorBuilder,
} = require('@discordjs/builders');

// 환경변수 헬퍼(.env, $env 둘 다 OK)
function env(name, fallback = '') {
  const v = process.env[name];
  return v && v.trim().length > 0 ? v.trim() : fallback;
}
const TOKEN = env('DISCORD_TOKEN');
const APP_ID_ENV = env('APP_ID');   // 없으면 런타임 봇 ID 사용
const GUILD_ID = env('GUILD_ID');   // 있으면 길드에만 등록(즉시), 없으면 전역(1~5분)

if (!TOKEN) {
  console.error('DISCORD_TOKEN 없음. $env:DISCORD_TOKEN="토큰"; node index.js 또는 .env에 설정해줘.');
  process.exit(1);
}

/* ========= 컨테이너(안전 구성) ========= */
function buildMainContainer() {
  // 제목
  const title = new TextDisplayBuilder().setContent('자동화 로벅스');
  const sectionTitle = new SectionBuilder().addTextDisplayComponents(title);

  // 인게임/게임패스 안내
  const line1 = new TextDisplayBuilder().setContent('인게임 패스, 게임패스 지원');

  // 막대기
  const sep1 = new SeparatorBuilder().setSpacing('Small');

  // 안내 + 문의 링크
  const line2 = new TextDisplayBuilder().setContent(
    '아래 버튼을 눌려 이용해주세요!\n' +
    '자충 오류시 [문의 바로가기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
  );

  // 막대기
  const sep2 = new SeparatorBuilder().setSpacing('Small');

  // 푸터
  const footer = new TextDisplayBuilder().setContent('자동화 로벅스 / 2025 / GMT+09:00');

  return new ContainerBuilder()
    .addSectionComponents(sectionTitle)
    .addTextDisplayComponents(line1)
    .addSeparatorComponents(sep1)
    .addTextDisplayComponents(line2)
    .addSeparatorComponents(sep2)
    .addTextDisplayComponents(footer);
}

/* ========= 버튼(컨테이너 아래 액션로우) =========
   이모지 포함 버전 — 이모지는 서버 커스텀 이모지 ID 사용
   - 커스텀 이모지: { name: '이름', id: '이모지ID' }
   - 유니코드 이모지: .setEmoji('🔔') 처럼 문자열로만 설정해도 됨
*/
function buildMainRows() {
  const btnNotice = new ButtonBuilder()
    .setCustomId('notice')
    .setLabel('공지사항')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' }) // <:emoji_5:1424003478275231916>
    .setStyle(ButtonStyle.Secondary);

  const btnCharge = new ButtonBuilder()
    .setCustomId('charge')
    .setLabel('충전')
    .setEmoji({ name: 'charge', id: '1424003480007475281' })  // <:charge:1424003480007475281>
    .setStyle(ButtonStyle.Secondary);

  const btnInfo = new ButtonBuilder()
    .setCustomId('info')
    .setLabel('내 정보')
    .setEmoji({ name: 'info', id: '1424003482247237908' })    // <:info:1424003482247237908>
    .setStyle(ButtonStyle.Secondary);

  const btnBuy = new ButtonBuilder()
    .setCustomId('buy')
    .setLabel('구매')
    .setEmoji({ name: 'category', id: '1424003481240469615' }) // <:category:1424003481240469615>
    .setStyle(ButtonStyle.Secondary);

  const row = new ActionRowBuilder().addComponents(btnNotice, btnCharge, btnInfo, btnBuy);
  return [row];
}

/* ========= “내 정보” 컨테이너(버튼 없음, 안전) ========= */
function buildProfileContainer({ username, balance, total, orders }) {
  const title = new TextDisplayBuilder().setContent(`**${username}님 정보**`);
  const sectionTitle = new SectionBuilder().addTextDisplayComponents(title);

  const sep = new SeparatorBuilder().setSpacing('Small');

  const line = new TextDisplayBuilder().setContent(
    `**남은 금액** = __${balance}원__\n` +
    `**누적 금액** = __${total}원__\n` +
    `**구매 횟수** = __${orders}번__`
  );

  return new ContainerBuilder()
    .addSectionComponents(sectionTitle)
    .addSeparatorComponents(sep)
    .addTextDisplayComponents(line);
}

/* ========= 커맨드 등록(중복 제거) ========= */
const client = new Client({ intents: [GatewayIntentBits.Guilds] });

client.once('ready', async (c) => {
  console.log(`${c.user.username} online`);
  const appId = APP_ID_ENV || c.user.id;
  const rest = new REST({ version: '10' }).setToken(TOKEN);

  try {
    // 전역/길드 모두 초기화(중복 완전 제거)
    await rest.put(Routes.applicationCommands(appId), { body: [] }).catch(() => {});
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(appId, GUILD_ID), { body: [] }).catch(() => {});
    }

    // 한 군데만 재등록
    const body = [{ name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' }];
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(appId, GUILD_ID), { body });
      console.log('길드 커맨드 등록 완료(즉시): /로벅스패널');
    } else {
      await rest.put(Routes.applicationCommands(appId), { body });
      console.log('전역 커맨드 등록 완료(반영 1~5분): /로벅스패널');
    }
  } catch (e) {
    console.error('커맨드 등록 실패:', e?.message || e);
  }
});

/* ========= 상호작용 ========= */
client.on('interactionCreate', async (interaction) => {
  // 슬래시 커맨드 → 패널 출력
  if (interaction.isChatInputCommand() && interaction.commandName === '로벅스패널') {
    try {
      await interaction.reply({
        flags: MessageFlags.IsComponentsV2,
        components: [
          buildMainContainer(),   // 컨테이너(텍스트/막대기만)
          ...buildMainRows(),     // 컨테이너 아래 버튼(이모지 포함)
        ],
      });
    } catch (e) {
      console.error('패널 전송 실패:', e?.message || e);
    }
    return;
  }

  // 버튼 묵음 처리(배너 안 뜨게)
  if (interaction.isButton()) {
    try { await interaction.deferUpdate(); } catch (_) {}

    // 내 정보 → 컨테이너로 프로필 표시
    if (interaction.customId === 'info') {
      try {
        const username = interaction.user.username;
        const userId = interaction.user.id;

        // 여기서 DB 붙이면 됨. 실패/없음에도 안전하게 기본값 리턴.
        const profile = await getUserProfileSafe(userId);

        const container = buildProfileContainer({
          username,
          balance: profile.balance,
          total: profile.total,
          orders: profile.orders,
        });

        await interaction.followUp({
          flags: MessageFlags.IsComponentsV2,
          components: [container], // 버튼 없이 컨테이너만
        });
      } catch (e) {
        console.error('내 정보 전송 실패:', e?.message || e);
      }
    }
  }
});

/* ========= DB 안전 헬퍼(더미) =========
   실제 DB 붙일 땐 이 함수 내용만 바꿔주면 됨.
*/
async function getUserProfileSafe(userId) {
  try {
    // TODO: 실제 DB 조회
    // 예) const row = await db.user.findById(userId);
    const row = null; // 더미

    if (!row) return { balance: 0, total: 0, orders: 0 };

    return {
      balance: Number(row.balance) || 0,
      total: Number(row.total) || 0,
      orders: Number(row.orders) || 0,
    };
  } catch (e) {
    console.error('DB 조회 실패:', e?.message || e);
    return { balance: 0, total: 0, orders: 0 };
  }
}

client.login(TOKEN);
