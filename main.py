require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  MessageFlags,
  TextDisplayBuilder,
  ButtonBuilder,
  ButtonStyle,
  ThumbnailBuilder,
  SectionBuilder,
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

    // const buttonComponent = new ButtonBuilder()
    //   .setCustomId('random-button-id')
    //   .setLabel('Click me')
    //   .setStyle(ButtonStyle.Primary);

    const thumbnailComponent = new ThumbnailBuilder({
      media: {
        url: 'https://cdn.discordapp.com/embeds/avatars/1.png',
      },
    });

    const sectionComponent = new SectionBuilder()
      .addTextDisplayComponents(textComponent, textComponent, textComponent)
      .setThumbnailAccessory(thumbnailComponent);

    message.channel.send({
      flags: MessageFlags.IsComponentsV2,
      components: [sectionComponent],
    });
  }
});

client.login(process.env.TOKEN);
