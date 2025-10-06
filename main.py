require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  MessageFlags,
  TextDisplayBuilder,
  ContainerBuilder,
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
    const textComponent = new TextDisplayBuilder().setContent(
      '자동화 로벅스(제목)\n아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 [오류 문의하기](https://discord.com/channels/1419200424636055592/1423477824865439884)'
    );

    const containerComponent = new ContainerBuilder().addTextDisplayComponents(
      textComponent,
      textComponent,
      textComponent
    );

    message.channel.send({
      flags: MessageFlags.IsComponentsV2,
      components: [containerComponent],
    });
  }
});

client.login(process.env.TOKEN);
