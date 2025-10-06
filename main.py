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

// 기존 슬래시 커맨드 초기화하고 /로벅스패널만 등록
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

  // 네가 준 텍스트와 줄바꿈 “그대로”
  const topText = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 문의하기'
  );

  // 여기에 “(긴 막대기)” — 간격 좁게
  const sep1 = new SeparatorBuilder().setSpacing('Small');

  const midStock = new TextDisplayBuilder().setContent(
    '로벅스 재고\n60초마다 갱신됩니다'
  );

  const midSales = new TextDisplayBuilder().setContent(
    '\n누적 판매량\n총 판매된 로벅스'
  );

  // 두 번째 “(긴 막대기)”
  const sep2 = new SeparatorBuilder().setSpacing('Small');

  const footer = new TextDisplayBuilder().setContent(
    '자동화 로벅스 / 2025 / GMT+09:00'
  );

  // 순서 및 막대기 위치 정확히 반영
  const container = new ContainerBuilder()
    .addTextDisplayComponents(topText)
    .addSeparatorComponents(sep1)
    .addTextDisplayComponents(midStock)
    .addTextDisplayComponents(midSales)
    .addSeparatorComponents(sep2)
    .addTextDisplayComponents(footer);

  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container],
  });
});

// messageCreate 핸들러(예: ping) 없음
client.login(process.env.DISCORD_TOKEN);
