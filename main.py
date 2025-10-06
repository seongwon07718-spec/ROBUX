require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  MessageFlags,
  // 확장 빌드에 포함된 빌더들 기준
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

// 슬래시 커맨드 초기화 → /로벅스패널만 등록
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
  const txtTop = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n' +
    '아래 버튼을 눌러 이용해주세요\n' +
    '자충 오류 문의는 문의하기'
  );
  const sectionTop = new SectionBuilder().addTextDisplayComponents(txtTop);

  // 2) 긴 막대기(간격 좁게)
  const sepTop = new SeparatorBuilder().setSpacing('Small');

  // 3) 재고 섹션 + 핑크 비활성 버튼
  const txtStock = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n' +
    '60초마다 갱신됩니다'
  );
  const btnStock = new ButtonBuilder()
    .setCustomId('stock_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);
  const sectionStock = new SectionBuilder()
    .addTextDisplayComponents(txtStock)
    .setButtonAccessory(btnStock);

  // 4) 누적 판매량 섹션 + 핑크 비활성 버튼
  const txtSales = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>누적 판매량**\n' +
    '총 판매된 로벅스'
  );
  const btnSales = new ButtonBuilder()
    .setCustomId('sales_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);
  const sectionSales = new SectionBuilder()
    .addTextDisplayComponents(txtSales)
    .setButtonAccessory(btnSales);

  // 5) 중간 긴 막대기
  const sepMid = new SeparatorBuilder().setSpacing('Small');

  // 6) 하단 2x2 버튼(회색, 활성) — 각 섹션에 버튼 두 개씩 액세서리로 붙임
  const btnNotice = new ButtonBuilder()
    .setCustomId('notice')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' })
    .setLabel('공지사항')
    .setStyle(ButtonStyle.Secondary);
  const btnCharge = new ButtonBuilder()
    .setCustomId('charge')
    .setEmoji({ name: 'charge', id: '1424003480007475281' })
    .setLabel('충전')
    .setStyle(ButtonStyle.Secondary);
  const btnInfo = new ButtonBuilder()
    .setCustomId('info')
    .setEmoji({ name: 'info', id: '1424003482247237908' })
    .setLabel('내 정보')
    .setStyle(ButtonStyle.Secondary);
  const btnBuy = new ButtonBuilder()
    .setCustomId('buy')
    .setEmoji({ name: 'category', id: '1424003481240469615' })
    .setLabel('구매')
    .setStyle(ButtonStyle.Secondary);

  // 빌드에 따라 setButtonAccessory를 여러 번 체이닝해도 되고,
  // setButtonAccessories([btn1, btn2]) 형식일 수도 있음.
  // 지금은 체이닝 지원 가정.
  const sectionBtnsRow1 = new SectionBuilder()
    .setButtonAccessory(btnNotice)
    .setButtonAccessory(btnCharge);

  const sectionBtnsRow2 = new SectionBuilder()
    .setButtonAccessory(btnInfo)
    .setButtonAccessory(btnBuy);

  // 7) 하단 긴 막대기
  const sepBottom = new SeparatorBuilder().setSpacing('Small');

  // 8) 푸터 섹션
  const txtFooter = new TextDisplayBuilder().setContent(
    '자동화 로벅스 / 2025 / GMT+09:00'
  );
  const sectionFooter = new SectionBuilder().addTextDisplayComponents(txtFooter);

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

// 하단 2x2 버튼은 누를 수 있게 하되, 화면 반응 배너는 안 뜨게 묵음 처리
client.on('interactionCreate', async (i) => {
  if (!i.isButton()) return;
  try { await i.deferUpdate(); } catch (_) {}
});

client.login(process.env.DISCORD_TOKEN);
