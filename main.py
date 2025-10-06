require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  MessageFlags,
  TextDisplayBuilder,
  ContainerBuilder,
  SeparatorBuilder,
  SeparatorSpacingSize,
} = require('discord.js');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

client.on('ready', (client) => {
  console.log(`${client.user.username} is online.`);
});

client.on('messageCreate', async (message) => {
  if (message.content === 'ping') {
    // 제목 텍스트
    const title = new TextDisplayBuilder().setContent('자동화 로벅스');

    // 긴 막대기(구분선)
    const separator = new SeparatorBuilder().setSpacing(SeparatorSpacingSize.Medium);

    // 본문 텍스트
    const body = new TextDisplayBuilder().setContent(
      '아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 [오류 문의하기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
    );

    // 컨테이너에 순서대로 추가: 제목 → 구분선 → 본문
    const container = new ContainerBuilder()
      .addTextDisplayComponents(title)
      .addSeparatorComponents(separator)
      .addTextDisplayComponents(body);

    await message.channel.send({
      flags: MessageFlags.IsComponentsV2,
      components: [container],
    });
  }
});

client.login(process.env.TOKEN);
