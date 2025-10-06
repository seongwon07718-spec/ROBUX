require('dotenv/config');
const { Client, GatewayIntentBits } = require('discord.js');
const { register } = require('./src/registerCommands');
const { bindInteractions } = require('./src/panel');

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

client.once('ready', async (c) => {
  console.log(`${c.user.username} online`);
  await register(c.user.id);
});

bindInteractions(client);
client.login(process.env.DISCORD_TOKEN);
