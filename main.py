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
      'This is the text display component'
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
