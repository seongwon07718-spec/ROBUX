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

// env 헬퍼(.env 또는 PowerShell $env 둘 다 지원)
function env(name, fallback = '') {
  const v = process.env[name];
  return v && v.trim().length > 0 ? v.trim() : fallback;
}
const TOKEN = env('DISCORD_TOKEN');
const APP_ID_ENV = env('APP_ID');   // 없으면 런타임 봇 ID 사용
const GUILD_ID = env('GUILD_ID');   // 있으면 길드에만 등록(즉시), 없으면 전역(1~5분)

if (!TOKEN) {
  console.error('DISCORD_TOKEN 없음. $env:DISCORD_TOKEN="토큰"; node index.js 또는 .env에 넣어줘.');
  process.exit(1);
}

// 컨테이너: 텍스트/막대기만 사용(안전 구성)
function buildContainer() {
  // 1) 제목
  const title = new TextDisplayBuilder().setContent('자동화 로벅스');
  const sectionTitle = new SectionBuilder().addTextDisplayComponents(title);

  // 2) 인게임/게임패스 안내
  const line1 = new TextDisplayBuilder().setContent('인게임 패스, 게임패스 지원');

  // 3) 구분선(막대기)
  const sep1 = new SeparatorBuilder().setSpacing('Small');

  // 4) 안내 문구 + 문의 링크
  const line2 = new TextDisplayBuilder().setContent(
    '아래 버튼을 눌려 이용해주세요!\n' +
    '자충 오류시 [문의 바로가기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
  );

  // 5) 구분선(막대기)
  const sep2 = new SeparatorBuilder().setSpacing('Small');

  // 6) 푸터
  const footer = new TextDisplayBuilder().setContent('자동화 로벅스 / 2025 / GMT+09:00');

  // 컨테이너 조립(텍스트/막대기만)
  return new ContainerBuilder()
    .addSectionComponents(sectionTitle)
    .addTextDisplayComponents(line1)
    .addSeparatorComponents(sep1)
    .addTextDisplayComponents(line2)
    .addSeparatorComponents(sep2)
    .addTextDisplayComponents(footer);
}

// 컨테이너 “아래”에 놓일 버튼(액션로우) — 안전한 공식 방식
function buildActionRows() {
  const btnNotice = new ButtonBuilder()
    .setCustomId('notice')
    .setLabel('공지사항')
    .setStyle(ButtonStyle.Secondary);

  const btnCharge = new ButtonBuilder()
    .setCustomId('charge')
    .setLabel('충전')
    .setStyle(ButtonStyle.Secondary);

  const btnInfo = new ButtonBuilder()
    .setCustomId('info')
    .setLabel('내 정보')
    .setStyle(ButtonStyle.Secondary);

  const btnBuy = new ButtonBuilder()
    .setCustomId('buy')
    .setLabel('구매')
    .setStyle(ButtonStyle.Secondary);

  // 5개 이상이면 로우를 나눠야 하는데 4개니까 한 줄에 배치 가능
  const row = new ActionRowBuilder().addComponents(btnNotice, btnCharge, btnInfo, btnBuy);
  return [row];
}

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

client.once('ready', async (c) => {
  console.log(`${c.user.username} online`);
  const appId = APP_ID_ENV || c.user.id;
  const rest = new REST({ version: '10' }).setToken(TOKEN);

  try {
    // 중복 방지: 전역/길드 모두 초기화
    await rest.put(Routes.applicationCommands(appId), { body: [] }).catch(() => {});
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(appId, GUILD_ID), { body: [] }).catch(() => {});
    }

    // 한 군데만 등록(길드 있으면 즉시, 없으면 전역)
    const body = [{ name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' }];
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(appId, GUILD_ID), { body });
      console.log('길드 커맨드 등록 완료(즉시 반영): /로벅스패널');
    } else {
      await rest.put(Routes.applicationCommands(appId), { body });
      console.log('전역 커맨드 등록 완료(반영 1~5분): /로벅스패널');
    }
  } catch (e) {
    console.error('커맨드 등록 실패:', e?.message || e);
  }
});

client.on('interactionCreate', async (interaction) => {
  // 슬래시 명령
  if (interaction.isChatInputCommand() && interaction.commandName === '로벅스패널') {
    try {
      await interaction.reply({
        flags: MessageFlags.IsComponentsV2,      // 컨테이너 v2 플래그
        components: [
          buildContainer(),                      // 컨테이너(텍스트/막대기)
          ...buildActionRows(),                  // 컨테이너 "아래" 액션로우 버튼
        ],
      });
    } catch (e) {
      console.error('패널 전송 실패:', e?.message || e);
    }
    return;
  }

  // 버튼은 눌러도 반응 배너 안 뜨게 묵음 처리(선택)
  if (interaction.isButton()) {
    try { await interaction.deferUpdate(); } catch (_) {}
  }
});

client.login(TOKEN);
