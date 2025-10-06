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
  ActionRowBuilder,
} = require('discord.js');

const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

// 기존 슬래시 커맨드 초기화 → /로벅스패널만 등록
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

  // 1) 상단 안내 텍스트
  const top = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n' +
    '아래 버튼을 눌러 이용해주세요\n' +
    '자충 오류 문의는 문의하기'
  );

  // 2) 긴 막대기(간격 좁게)
  const sepTop = new SeparatorBuilder().setSpacing('Small');

  // 3) 재고 섹션 텍스트
  const stockText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n' +
    '60초마다 갱신됩니다'
  );

  // 3-1) 재고 섹션 “0로벅스” 버튼(핑크, 비활성)
  const stockBtn = new ButtonBuilder()
    .setCustomId('stock_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger) // 핑크 계열
    .setDisabled(true);

  // 4) 누적 판매량 섹션 텍스트
  const salesText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>누적 판매량**\n' +
    '총 판매된 로벅스'
  );

  // 4-1) 누적 판매량 “0로벅스” 버튼(핑크, 비활성)
  const salesBtn = new ButtonBuilder()
    .setCustomId('sales_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);

  // 5) 중간 긴 막대기
  const sepMid = new SeparatorBuilder().setSpacing('Small');

  // 6) 하단 2x2 버튼(공지/충전/내 정보/구매) — 회색, 활성(누를 수 있게)
  const noticeBtn = new ButtonBuilder()
    .setCustomId('notice')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' }) // <:emoji_5:1424003478275231916>
    .setLabel('공지사항')
    .setStyle(ButtonStyle.Secondary)
    .setDisabled(false);

  const chargeBtn = new ButtonBuilder()
    .setCustomId('charge')
    .setEmoji({ name: 'charge', id: '1424003480007475281' }) // <:charge:1424003480007475281>
    .setLabel('충전')
    .setStyle(ButtonStyle.Secondary)
    .setDisabled(false);

  const infoBtn = new ButtonBuilder()
    .setCustomId('info')
    .setEmoji({ name: 'info', id: '1424003482247237908' }) // <:info:1424003482247237908>
    .setLabel('내 정보')
    .setStyle(ButtonStyle.Secondary)
    .setDisabled(false);

  const buyBtn = new ButtonBuilder()
    .setCustomId('buy')
    .setEmoji({ name: 'category', id: '1424003481240469615' }) // <:category:1424003481240469615>
    .setLabel('구매')
    .setStyle(ButtonStyle.Secondary)
    .setDisabled(false);

  // 2x2 배열(두 줄)
  const row1 = new ActionRowBuilder().addComponents(noticeBtn, chargeBtn);
  const row2 = new ActionRowBuilder().addComponents(infoBtn, buyBtn);

  // 7) 하단 긴 막대기
  const sepBottom = new SeparatorBuilder().setSpacing('Small');

  // 8) 푸터 텍스트
  const footer = new TextDisplayBuilder().setContent(
    '자동화 로벅스 / 2025 / GMT+09:00'
  );

  // 전부 “컨테이너” 안에서 순서대로 표시
  const container = new ContainerBuilder()
    .addTextDisplayComponents(top)
    .addSeparatorComponents(sepTop)
    .addTextDisplayComponents(stockText)
    .addButtonComponents(stockBtn)   // 재고 버튼(비활성)
    .addTextDisplayComponents(salesText)
    .addButtonComponents(salesBtn)   // 누적 버튼(비활성)
    .addSeparatorComponents(sepMid)
    .addButtonComponents(noticeBtn, chargeBtn) // 2x2 버튼 1행
    .addButtonComponents(infoBtn, buyBtn)      // 2x2 버튼 2행
    .addSeparatorComponents(sepBottom)
    .addTextDisplayComponents(footer);

  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container],
  });
});

// 하단 2x2 버튼은 “누를 수 있게” 활성화했지만, 지금은 반응 안 뜨게 처리
client.on('interactionCreate', async (i) => {
  if (!i.isButton()) return;
  // 공지/충전/내 정보/구매 버튼 눌러도 아무 반응 X
  try {
    await i.deferUpdate(); // 상호작용 표시 없이 조용히 넘김
  } catch (_) {}
});

client.login(process.env.DISCORD_TOKEN);
