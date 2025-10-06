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
  SeparatorSpacingSize,
} = require('discord.js');

const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

// 슬래시 커맨드: /로벅스패널
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
    // 전역 커맨드 등록 → 기존 커맨드 싹 초기화됨
    await rest.put(Routes.applicationCommands(c.user.id), { body: commands });
    console.log('슬래시 커맨드 초기화 및 등록 완료: /로벅스패널');
  } catch (err) {
    console.error('커맨드 등록 실패:', err);
  }
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== '로벅스패널') return;

  const title = new TextDisplayBuilder().setContent('자동화 로벅스');
  const separator = new SeparatorBuilder().setSpacing(SeparatorSpacingSize.Medium);
  const body = new TextDisplayBuilder().setContent(
    '아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 [오류 문의하기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
  );

  const container = new ContainerBuilder()
    .addTextDisplayComponents(title)
    .addSeparatorComponents(separator)
    .addTextDisplayComponents(body);

  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container],
  });
});

client.login(process.env.DISCORD_TOKEN);
