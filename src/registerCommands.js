require('dotenv/config');
const { REST, Routes } = require('discord.js');

const TOKEN = process.env.DISCORD_TOKEN;
const APP_ID = process.env.APP_ID;
const GUILD_ID = process.env.GUILD_ID || '';

const commands = [
  { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
];

async function register(appId) {
  const rest = new (require('discord.js').REST)({ version: '10' }).setToken(TOKEN);
  const id = appId || APP_ID;
  if (!TOKEN) throw new Error('DISCORD_TOKEN 누락');

  // 중복 제거: 전역/길드 싹 비우고 한 군데만 등록
  try {
    await rest.put(Routes.applicationCommands(id), { body: [] }).catch(() => {});
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(id, GUILD_ID), { body: [] }).catch(() => {});
      await rest.put(Routes.applicationGuildCommands(id, GUILD_ID), { body: commands });
      console.log('길드 등록 완료: /로벅스패널 (즉시 반영)');
    } else {
      await rest.put(Routes.applicationCommands(id), { body: commands });
      console.log('전역 등록 완료: /로벅스패널 (반영 수 분 소요)');
    }
  } catch (err) {
    console.error('커맨드 등록 실패:', err?.message || err);
  }
}

module.exports = { register };
