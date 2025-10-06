require('dotenv/config');
const { REST, Routes } = require('discord.js');

const TOKEN = process.env.DISCORD_TOKEN;
const APP_ID_ENV = process.env.APP_ID;
const GUILD_ID = process.env.GUILD_ID || '';

const commands = [
  { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
];

async function register(runtimeAppId) {
  if (!TOKEN) throw new Error('DISCORD_TOKEN 누락');
  const appId = APP_ID_ENV || runtimeAppId;
  const rest = new REST({ version: '10' }).setToken(TOKEN);

  try {
    // 전역/길드 싹 비우고 하나만 등록
    await rest.put(Routes.applicationCommands(appId), { body: [] }).catch(()=>{});
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(appId, GUILD_ID), { body: [] }).catch(()=>{});
      await rest.put(Routes.applicationGuildCommands(appId, GUILD_ID), { body: commands });
      console.log('길드 등록 완료: /로벅스패널 (즉시 반영)');
    } else {
      await rest.put(Routes.applicationCommands(appId), { body: commands });
      console.log('전역 등록 완료: /로벅스패널 (반영 수 분)');
    }
  } catch (err) {
    console.error('커맨드 등록 실패:', err?.message || err);
  }
}

module.exports = { register };
