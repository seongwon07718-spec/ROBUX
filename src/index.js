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
} = require('discord.js');

const {
  ContainerBuilder,
  SectionBuilder,
  TextDisplayBuilder,
  SeparatorBuilder,
} = require('@discordjs/builders');

// 환경변수 우선 → 없으면 .env 읽기
function env(name, fallback = '') {
  const v = process.env[name];
  return v && v.trim().length > 0 ? v.trim() : fallback;
}

const TOKEN = env('DISCORD_TOKEN');
const APP_ID_ENV = env('APP_ID'); // 없으면 런타임에서 대체

if (!TOKEN) {
  console.error('DISCORD_TOKEN이 비어있음. PowerShell에선 $env:DISCORD_TOKEN="토큰"; node index.js 또는 .env에 넣어.');
  process.exit(1);
}

// 섹션에 버튼 액세서리 붙이는 헬퍼(빌드별 API 자동 매칭)
function attachButtonsToSection(section, buttons) {
  const arr = Array.isArray(buttons) ? buttons : [buttons];

  // 일부 빌드는 레이아웃 전환 필요
  if (typeof section.setLayout === 'function') {
    try { section.setLayout('withButtonAccessory'); } catch (_) {}
  }

  if (typeof section.setButtonAccessory === 'function' && arr.length === 1) {
    return section.setButtonAccessory(arr[0]);
  }
  if (typeof section.setButtonAccessories === 'function') {
    return section.setButtonAccessories(arr);
  }
  if (typeof section.addButtonAccessories === 'function') {
    return section.addButtonAccessories(arr);
  }
  if (typeof section.setAccessories === 'function') {
    return section.setAccessories({ buttons: arr });
  }
  throw new Error('섹션 버튼 액세서리 메서드를 찾지 못함(@discordjs/builders d.ts 확인 필요).');
}

function buildContainer() {
  // 상단 안내
  const topText = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n' +
    '아래 버튼을 눌러 이용해주세요\n' +
    '자충 오류 문의는 문의하기'
  );
  const sectionTop = new SectionBuilder().addTextDisplayComponents(topText);

  // 막대기(좁게)
  const sepTop = new SeparatorBuilder().setSpacing('Small');

  // 재고 섹션 + 핑크 비활성 버튼
  const stockText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n' +
    '60초마다 갱신됩니다'
  );
  const stockBtn = new ButtonBuilder()
    .setCustomId('stock_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger) // 핑크/레드톤
    .setDisabled(true);           // 못 누르게
  let sectionStock = new SectionBuilder().addTextDisplayComponents(stockText);
  sectionStock = attachButtonsToSection(sectionStock, stockBtn);

  // 누적 섹션 + 핑크 비활성 버튼
  const salesText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>누적 판매량**\n' +
    '총 판매된 로벅스'
  );
  const salesBtn = new ButtonBuilder()
    .setCustomId('sales_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);
  let sectionSales = new SectionBuilder().addTextDisplayComponents(salesText);
  sectionSales = attachButtonsToSection(sectionSales, salesBtn);

  // 중간 막대기
  const sepMid = new SeparatorBuilder().setSpacing('Small');

  // 하단 2x2(회색, 활성)
  const noticeBtn = new ButtonBuilder()
    .setCustomId('notice')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' })
    .setLabel('공지사항')
    .setStyle(ButtonStyle.Secondary);

  const chargeBtn = new ButtonBuilder()
    .setCustomId('charge')
    .setEmoji({ name: 'charge', id: '1424003480007475281' })
    .setLabel('충전')
    .setStyle(ButtonStyle.Secondary);

  const infoBtn = new ButtonBuilder()
    .setCustomId('info')
    .setEmoji({ name: 'info', id: '1424003482247237908' })
    .setLabel('내 정보')
    .setStyle(ButtonStyle.Secondary);

  const buyBtn = new ButtonBuilder()
    .setCustomId('buy')
    .setEmoji({ name: 'category', id: '1424003481240469615' })
    .setLabel('구매')
    .setStyle(ButtonStyle.Secondary);

  // 섹션 4개(섹션당 버튼 1개 → 검증 안전)
  let sectionBtnNotice = new SectionBuilder();
  sectionBtnNotice = attachButtonsToSection(sectionBtnNotice, noticeBtn);

  let sectionBtnCharge = new SectionBuilder();
  sectionBtnCharge = attachButtonsToSection(sectionBtnCharge, chargeBtn);

  let sectionBtnInfo = new SectionBuilder();
  sectionBtnInfo = attachButtonsToSection(sectionBtnInfo, infoBtn);

  let sectionBtnBuy = new SectionBuilder();
  sectionBtnBuy = attachButtonsToSection(sectionBtnBuy, buyBtn);

  // 하단 막대기
  const sepBottom = new SeparatorBuilder().setSpacing('Small');

  // 푸터
  const footerText = new TextDisplayBuilder().setContent('자동화 로벅스 / 2025 / GMT+09:00');
  const sectionFooter = new SectionBuilder().addTextDisplayComponents(footerText);

  // 컨테이너 조립(전부 컨테이너 안)
  return new ContainerBuilder()
    .addSectionComponents(sectionTop)
    .addSeparatorComponents(sepTop)
    .addSectionComponents(sectionStock)
    .addSectionComponents(sectionSales)
    .addSeparatorComponents(sepMid)
    .addSectionComponents(sectionBtnNotice)
    .addSectionComponents(sectionBtnCharge)
    .addSectionComponents(sectionBtnInfo)
    .addSectionComponents(sectionBtnBuy)
    .addSeparatorComponents(sepBottom)
    .addSectionComponents(sectionFooter);
}

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

client.once('ready', async (c) => {
  console.log(`${c.user.username} online`);
  const appId = APP_ID_ENV || c.user.id;
  const rest = new REST({ version: '10' }).setToken(TOKEN);

  try {
    // 전역 명령 싹 비우고 → 하나만 등록(중복 방지)
    await rest.put(Routes.applicationCommands(appId), { body: [] }).catch(() => {});
    await rest.put(Routes.applicationCommands(appId), {
      body: [
        { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
      ],
    });
    console.log('전역 커맨드 등록 완료(반영까지 수 분)');
  } catch (err) {
    console.error('커맨드 등록 실패:', err?.message || err);
  }
});

// 슬래시 명령과 버튼 상호작용
client.on('interactionCreate', async (interaction) => {
  // 패널 명령
  if (interaction.isChatInputCommand() && interaction.commandName === '로벅스패널') {
    try {
      await interaction.reply({
        flags: MessageFlags.IsComponentsV2,
        components: [buildContainer()],
      });
    } catch (e) {
      console.error('패널 전송 실패:', e?.message || e);
    }
    return;
  }

  // 하단 2x2 버튼: 눌러도 화면 반응 배너 안 뜨게 묵음 처리
  if (interaction.isButton()) {
    try { await interaction.deferUpdate(); } catch (_) {}
  }
});

client.login(TOKEN);
