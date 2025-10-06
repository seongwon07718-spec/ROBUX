require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  MessageFlags,
  TextDisplayBuilder,
  ContainerBuilder,
  SeparatorBuilder,
  ButtonBuilder,
  ButtonStyle,
} = require('discord.js');

const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

// 기존 슬래시 명령 초기화 → /로벅스패널만 등록
const commands = [
  { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
];

client.once('ready', async (c) => {
  console.log(`${c.user.username} is online.`);
  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  try {
    await rest.put(Routes.applicationCommands(c.user.id), { body: commands });
    console.log('슬래시 커맨드 등록 완료: /로벅스패널');
  } catch (err) {
    console.error('커맨드 등록 실패:', err);
  }
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== '로벅스패널') return;

  // 상단 안내 텍스트(그대로)
  const top = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n' +
    '아래 버튼을 눌러 이용해주세요\n' +
    '자충 오류 문의는 문의하기'
  );

  // 긴 막대기(간격 좁게)
  const sepTop = new SeparatorBuilder().setSpacing('Small');

  // 재고 섹션
  const stockText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n' +
    '60초마다 갱신됩니다'
  );
  // 핑크 비활성 버튼
  const stockBtn = new ButtonBuilder()
    .setCustomId('stock_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);

  // 누적 판매량 섹션
  const salesText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>누적 판매량**\n' +
    '총 판매된 로벅스'
  );
  // 핑크 비활성 버튼
  const salesBtn = new ButtonBuilder()
    .setCustomId('sales_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);

  // 중간 긴 막대기
  const sepMid = new SeparatorBuilder().setSpacing('Small');

  // 하단 2x2 버튼(회색, 활성) — PartialEmoji로 setEmoji
  const noticeBtn = new ButtonBuilder()
    .setCustomId('notice')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' })   // <:emoji_5:1424003478275231916>
    .setLabel('공지사항')
    .setStyle(ButtonStyle.Secondary);

  const chargeBtn = new ButtonBuilder()
    .setCustomId('charge')
    .setEmoji({ name: 'charge', id: '1424003480007475281' })    // <:charge:1424003480007475281>
    .setLabel('충전')
    .setStyle(ButtonStyle.Secondary);

  const infoBtn = new ButtonBuilder()
    .setCustomId('info')
    .setEmoji({ name: 'info', id: '1424003482247237908' })      // <:info:1424003482247237908>
    .setLabel('내 정보')
    .setStyle(ButtonStyle.Secondary);

  const buyBtn = new ButtonBuilder()
    .setCustomId('buy')
    .setEmoji({ name: 'category', id: '1424003481240469615' })  // <:category:1424003481240469615>
    .setLabel('구매')
    .setStyle(ButtonStyle.Secondary);

  // 하단 긴 막대기
  const sepBottom = new SeparatorBuilder().setSpacing('Small');

  // 푸터
  const footer = new TextDisplayBuilder().setContent(
    '자동화 로벅스 / 2025 / GMT+09:00'
  );

  // 전부 컨테이너 내부에 순서대로 배치 (텍스트/막대기/버튼 전부 add*Components)
  const container = new ContainerBuilder()
    .addTextDisplayComponents(top)
    .addSeparatorComponents(sepTop)
    .addTextDisplayComponents(stockText)
    .addButtonComponents(stockBtn)        // 핑크 비활성
    .addTextDisplayComponents(salesText)
    .addButtonComponents(salesBtn)        // 핑크 비활성
    .addSeparatorComponents(sepMid)
    .addButtonComponents(noticeBtn, chargeBtn) // 2x2 1행
    .addButtonComponents(infoBtn, buyBtn)      // 2x2 2행
    .addSeparatorComponents(sepBottom)
    .addTextDisplayComponents(footer);

  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container],
  });
});

// 하단 2x2 버튼은 누를 수 있지만, 화면 상호작용 배너 안 뜨게 조용 처리
client.on('interactionCreate', async (i) => {
  if (!i.isButton()) return;
  // 재고/누적은 disabled라 이벤트 자체가 안 옴. 하단 2x2만 들어옴 → 묵음 처리
  try {
    await i.deferUpdate();
  } catch (_) {}
});

client.login(process.env.DISCORD_TOKEN);
