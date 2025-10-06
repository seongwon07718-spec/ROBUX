addSectionComponents 방식)
require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  MessageFlags,
  // 아래 빌더들은 네가 쓰는 components-v2 확장 빌드 기준
  TextDisplayBuilder,
  ContainerBuilder,
  SectionBuilder,
  SeparatorBuilder,
  ButtonBuilder,
  ButtonStyle,
} = require('discord.js');

const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

// /로벅스패널 한 개만 등록
const commands = [
  { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
];

client.once('ready', async (c) => {
  console.log(`${c.user.username} is online.`);
  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  await rest.put(Routes.applicationCommands(c.user.id), { body: commands });
  console.log('슬래시 커맨드 등록 완료: /로벅스패널');
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== '로벅스패널') return;

  // 1) 상단 안내 섹션
  const topText = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n' +
    '아래 버튼을 눌러 이용해주세요\n' +
    '자충 오류 문의는 문의하기'
  );
  const sectionTop = new SectionBuilder().addTextDisplayComponents(topText);

  // 2) 상단 긴 막대기
  const sepTop = new SeparatorBuilder().setSpacing('Small');

  // 3) 재고 섹션 + 핑크 버튼(비활성)
  const stockText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n' +
    '60초마다 갱신됩니다'
  );
  const stockBtn = new ButtonBuilder()
    .setCustomId('stock_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger) // 핑크 계열
    .setDisabled(true);
  const sectionStock = new SectionBuilder()
    .addTextDisplayComponents(stockText)
    .setButtonAccessory(stockBtn);

  // 4) 누적 섹션 + 핑크 버튼(비활성)
  const salesText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>누적 판매량**\n' +
    '총 판매된 로벅스'
  );
  const salesBtn = new ButtonBuilder()
    .setCustomId('sales_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);
  const sectionSales = new SectionBuilder()
    .addTextDisplayComponents(salesText)
    .setButtonAccessory(salesBtn);

  // 5) 중간 긴 막대기
  const sepMid = new SeparatorBuilder().setSpacing('Small');

  // 6) 하단 2x2 버튼(회색, 활성) — 버튼은 섹션 2개로 쪼개서 2x2 배치
  //    이 섹션들은 텍스트 없이 버튼 액세서리만 두 개씩 붙여서 2x2처럼 보이게
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

  // 2x2: 위 행
  const sectionBtnsRow1 = new SectionBuilder()
    .setButtonAccessory(noticeBtn)
    .setButtonAccessory(chargeBtn); // 빌드에 따라 setButtonAccessory로 여러 개 체이닝 지원
  // 2x2: 아래 행
  const sectionBtnsRow2 = new SectionBuilder()
    .setButtonAccessory(infoBtn)
    .setButtonAccessory(buyBtn);

  // 7) 하단 긴 막대기
  const sepBottom = new SeparatorBuilder().setSpacing('Small');

  // 8) 푸터 섹션
  const footerText = new TextDisplayBuilder().setContent(
    '자동화 로벅스 / 2025 / GMT+09:00'
  );
  const sectionFooter = new SectionBuilder().addTextDisplayComponents(footerText);

  // 컨테이너에 섹션/구분선 순서대로 배치
  const container = new ContainerBuilder()
    .addSectionComponents(sectionTop)
    .addSeparatorComponents(sepTop)
    .addSectionComponents(sectionStock)
    .addSectionComponents(sectionSales)
    .addSeparatorComponents(sepMid)
    .addSectionComponents(sectionBtnsRow1)
    .addSectionComponents(sectionBtnsRow2)
    .addSeparatorComponents(sepBottom)
    .addSectionComponents(sectionFooter);

  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container],
  });
});

// 하단 2x2 버튼은 “누를 수 있게”지만 화면 반응은 안 뜨게 묵음 처리
client.on('interactionCreate', async (i) => {
  if (!i.isButton()) return;
  try { await i.deferUpdate(); } catch (_) {}
});

client.login(process.env.DISCORD_TOKEN);
