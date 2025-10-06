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

// 전부 초기화하고 /로벅스패널만
const commands = [
  { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
];

client.once('ready', async (c) => {
  console.log(`${c.user.username} is online.`);
  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  try {
    await rest.put(Routes.applicationCommands(c.user.id), { body: commands });
    console.log('슬래시 커맨드 초기화 및 등록 완료: /로벅스패널');
  } catch (err) {
    console.error('커맨드 등록 실패:', err);
  }
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== '로벅스패널') return;

  // 상단 텍스트 블록
  const top = new TextDisplayBuilder().setContent(
    '**자동화 로벅스**\n' +
    '아래 버튼을 눌러 이용해주세요\n' +
    '자충 오류 문의는 [문의하기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
  );

  // 긴 막대기(간격 좁게)
  const sep1 = new SeparatorBuilder().setSpacing('Small');

  // 재고 섹션
  // 애니메 이모지는 PartialEmoji: <a:upuoipipi:1423892277373304862>
  const stock = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n' +
    '60초마다 갱신됩니다'
  );
  // 0로벅스 버튼(핑크, 비활성)
  const stockButton = new ButtonBuilder()
    .setCustomId('stock_zero') // disabled라 상호작용 안 됨
    .setLabel('186개') // 예시 이미지 느낌 유지 원하면 '0로벅스' 대신 숫자 표기 바꿔도 됨
    .setStyle(ButtonStyle.Danger) // 핑크톤은 보통 Danger(빨/분홍 계열)
    .setDisabled(true);

  // 누적 판매량 섹션
  const sales = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>누적 판매량**\n' +
    '총 판매된 로벅스'
  );
  const salesButton = new ButtonBuilder()
    .setCustomId('sales_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger) // 핑크
    .setDisabled(true);

  // 두 번째 긴 막대기
  const sep2 = new SeparatorBuilder().setSpacing('Small');

  // 하단 2x2 버튼(공지/충전/내 정보/구매) — 회색, 비활성
  // 커스텀 이모지들은 PartialEmoji 문자열로 버튼 라벨에 포함시킬 수 없으니, 이모지를 setEmoji로 설정
  const noticeBtn = new ButtonBuilder()
    .setCustomId('notice')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' }) // <:emoji_5:1424003478275231916>
    .setLabel('공지사항')
    .setStyle(ButtonStyle.Secondary) // 회색
    .setDisabled(true);

  const chargeBtn = new ButtonBuilder()
    .setCustomId('charge')
    .setEmoji({ name: 'charge', id: '1424003480007475281' }) // <:charge:1424003480007475281>
    .setLabel('충전')
    .setStyle(ButtonStyle.Secondary)
    .setDisabled(true);

  const infoBtn = new ButtonBuilder()
    .setCustomId('info')
    .setEmoji({ name: 'info', id: '1424003482247237908' }) // <:info:1424003482247237908>
    .setLabel('내 정보')
    .setStyle(ButtonStyle.Secondary)
    .setDisabled(true);

  const buyBtn = new ButtonBuilder()
    .setCustomId('buy')
    .setEmoji({ name: 'category', id: '1424003481240469615' }) // <:category:1424003481240469615>
    .setLabel('구매')
    .setStyle(ButtonStyle.Secondary)
    .setDisabled(true);

  // 2x2 배열 → 액션로우 2줄
  const row1 = new ActionRowBuilder().addComponents(noticeBtn, chargeBtn);
  const row2 = new ActionRowBuilder().addComponents(infoBtn, buyBtn);

  // 마지막 긴 막대기와 푸터
  const sep3 = new SeparatorBuilder().setSpacing('Small');
  const footer = new TextDisplayBuilder().setContent(
    '자동화 로벅스 / 2025 / GMT+09:00'
  );

  // 텍스트 컴포넌트 컨테이너: 상단 → 막대기 → 재고 → 누적 → 막대기 → 푸터
  const container = new ContainerBuilder()
    .addTextDisplayComponents(top)
    .addSeparatorComponents(sep1)
    .addTextDisplayComponents(stock)
    .addTextDisplayComponents(sales)
    .addSeparatorComponents(sep2)
    .addTextDisplayComponents(footer);

  // 메시지 전송: 텍스트 컴포넌트 + 버튼들
  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container, row1, row2],
  });
});

// 버튼 눌러도 반응 안 뜨게: 굳이 처리 안 함(전부 disabled)
client.login(process.env.DISCORD_TOKEN);
