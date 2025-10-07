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

// env 헬퍼(.env, PowerShell $env 모두 지원)
function env(name, fallback = '') {
  const v = process.env[name];
  return v && v.trim().length > 0 ? v.trim() : fallback;
}
const TOKEN = env('DISCORD_TOKEN');
const APP_ID_ENV = env('APP_ID');   // 없으면 런타임 봇 ID 사용
const GUILD_ID = env('GUILD_ID');   // 있으면 길드 등록(즉시), 없으면 전역 등록(1~5분)

if (!TOKEN) {
  console.error('DISCORD_TOKEN 없음. $env:DISCORD_TOKEN="토큰"; node index.js 또는 .env에 넣어줘.');
  process.exit(1);
}

/* ========= 컨테이너(텍스트/막대기만) ========= */
function buildMainContainer() {
  const title = new TextDisplayBuilder().setContent('자동화 로벅스');
  const sectionTitle = new SectionBuilder().addTextDisplayComponents(title);

  const line1 = new TextDisplayBuilder().setContent('인게임 패스, 게임패스 지원');
  const sep1 = new SeparatorBuilder().setSpacing('Small');

  const line2 = new TextDisplayBuilder().setContent(
    '아래 버튼을 눌려 이용해주세요!\n' +
    '자충 오류시 [문의 바로가기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
  );
  const sep2 = new SeparatorBuilder().setSpacing('Small');

  const footer = new TextDisplayBuilder().setContent('자동화 로벅스 / 2025 / GMT+09:00');

  // **수정: Components V2 컴포넌트는 .toJSON()으로 변환되어야 합니다.**
  return new ContainerBuilder()
    .addSectionComponents(sectionTitle)
    .addTextDisplayComponents(line1)
    .addSeparatorComponents(sep1)
    .addTextDisplayComponents(line2)
    .addSeparatorComponents(sep2)
    .addTextDisplayComponents(footer).toJSON(); 
}

/* ========= 액션로우 버튼(컨테이너 아래) ========= */
function buildMainRows() {
  const btnNotice = new ButtonBuilder()
    .setCustomId('notice')
    .setLabel('공지사항')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' })
    .setStyle(ButtonStyle.Secondary);

  const btnCharge = new ButtonBuilder()
    .setCustomId('charge')
    .setLabel('충전')
    .setEmoji({ name: 'charge', id: '1424003480007475281' })
    .setStyle(ButtonStyle.Secondary);

  const btnInfo = new ButtonBuilder()
    .setCustomId('info')
    .setLabel('내 정보')
    .setEmoji({ name: 'info', id: '1424003482247237908' })
    .setStyle(ButtonStyle.Secondary);

  const btnBuy = new ButtonBuilder()
    .setCustomId('buy')
    .setLabel('구매')
    .setEmoji({ name: 'category', id: '1424003481240469615' })
    .setStyle(ButtonStyle.Secondary);

  return [new ActionRowBuilder().addComponents(btnNotice, btnCharge, btnInfo, btnBuy)];
}

/* ========= “내 정보” 컨테이너(버튼 없음) ========= */
function buildProfileContainer({ username, balance, total, orders }) {
  const title = new TextDisplayBuilder().setContent(`**${username}님 정보**`);
  const sectionTitle = new SectionBuilder().addTextDisplayComponents(title);

  const sep = new SeparatorBuilder().setSpacing('Small');

  const line = new TextDisplayBuilder().setContent(
    `**남은 금액** = __${balance}원__\n` +
    `**누적 금액** = __${total}원__\n` +
    `**구매 횟수** = __${orders}번__`
  );

  // **수정: Components V2 컴포넌트는 .toJSON()으로 변환되어야 합니다.**
  return new ContainerBuilder()
    .addSectionComponents(sectionTitle)
    .addSeparatorComponents(sep)
    .addTextDisplayComponents(line).toJSON();
}

/* ========= DB 안전 헬퍼(더미) =========
   실제 DB 붙일 때 이 함수만 교체하면 됨.
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

/* ========= 클라이언트/등록/핸들러 ========= */
const client = new Client({ intents: [GatewayIntentBits.Guilds] });

client.once('ready', async (c) => {
  console.log(`${c.user.username} online`);
  const appId = APP_ID_ENV || c.user.id;
  const rest = new REST({ version: '10' }).setToken(TOKEN);

  try {
    // 중복 제거: 전역/길드 모두 초기화
    await rest.put(Routes.applicationCommands(appId), { body: [] }).catch(() => {});
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(appId, GUILD_ID), { body: [] }).catch(() => {});
    }

    // 한 군데만 등록
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

client.on('interactionCreate', async (interaction) => {
  // 슬래시 커맨드 → 패널 출력
  if (interaction.isChatInputCommand() && interaction.commandName === '로벅스패널') {
    try {
      // **수정: Container JSON과 ActionRowBuilder 배열을 합쳐서 전달**
      await interaction.reply({
        flags: MessageFlags.IsComponentsV2,
        components: [
          buildMainContainer(),   // 컨테이너 (JSON)
          ...buildMainRows(),     // 액션 로우 (Builder)
        ],
      });
    } catch (e) {
      console.error('패널 전송 실패:', e?.message || e);
    }
    return;
  }

  // 버튼 묵음 처리
  if (interaction.isButton()) {
    try { await interaction.deferUpdate(); } catch (_) {}

    if (interaction.customId === 'info') {
      try {
        const profile = await getUserProfileSafe(interaction.user.id);
        const container = buildProfileContainer({
          username: interaction.user.username,
          balance: profile.balance,
          total: profile.total,
          orders: profile.orders,
        });
        await interaction.followUp({
          flags: MessageFlags.IsComponentsV2 | MessageFlags.Ephemeral, // **수정: Ephemeral(임시) 플래그 추가**
          components: [container], // 컨테이너 (JSON)
        });
      } catch (e) {
        console.error('내 정보 전송 실패:', e?.message || e);
      }
    }
  }
});

client.login(TOKEN);
