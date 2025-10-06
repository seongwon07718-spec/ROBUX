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
} = require('discord.js');

const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

// 슬래시 커맨드: /로벅스패널만 등록(기존 싹 초기화)
const commands = [
  {
    name: '로벅스패널',
    description: '자동화 로벅스 패널을 표시합니다.',
  },
];

client.once('ready', async (c) => {
  console.log(`${c.user.username} is online.`);

  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  try {
    // 전역 커맨드 덮어쓰기 → /로벅스패널만 남김
    await rest.put(Routes.applicationCommands(c.user.id), { body: commands });
    console.log('슬래시 커맨드 초기화 및 등록 완료: /로벅스패널');
  } catch (err) {
    console.error('커맨드 등록 실패:', err);
  }
});

// /로벅스패널 실행 시 패널 전송
client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== '로벅스패널') return;

  // 섹션별 컴포넌트 구성
  const title = new TextDisplayBuilder().setContent('**자동화 로벅스**');
  const sep1 = new SeparatorBuilder().setSpacing('Large');

  const intro = new TextDisplayBuilder().setContent(
    '아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 [문의하기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
  );
  const sep2 = new SeparatorBuilder().setSpacing('Large');

  const stock = new TextDisplayBuilder().setContent(
    '**로벅스 재고**\n60초마다 갱신됩니다'
  );
  const sep3 = new SeparatorBuilder().setSpacing('Large');

  const sales = new TextDisplayBuilder().setContent(
    '**누적 판매량**\n총 판매된 로벅스'
  );
  const sep4 = new SeparatorBuilder().setSpacing('Large');

  const footer = new TextDisplayBuilder().setContent(
    '자동화 로벅스 / 2025 / GMT+09:00'
  );

  // 순서: 제목 → 막대기 → 안내 → 막대기 → 재고 → 막대기 → 누적 → 막대기 → 푸터
  const container = new ContainerBuilder()
    .addTextDisplayComponents(title)
    .addSeparatorComponents(sep1)
    .addTextDisplayComponents(intro)
    .addSeparatorComponents(sep2)
    .addTextDisplayComponents(stock)
    .addSeparatorComponents(sep3)
    .addTextDisplayComponents(sales)
    .addSeparatorComponents(sep4)
    .addTextDisplayComponents(footer);

  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container],
  });
});

// messageCreate(ping 등) 핸들러 없음
client.login(process.env.DISCORD_TOKEN);
