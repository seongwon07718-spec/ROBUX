const { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder, ComponentType, codeBlock } = require('discord.js');
require('dotenv').config();
const fs = require('fs');
const path = require('path');

const TOKEN = process.env.DISCORD_TOKEN;
const GUILD_ID = process.env.GUILD_ID || '';
if (!TOKEN) { console.error('[ENV] DISCORD_TOKEN 누락'); process.exit(1); }

// Client 객체 정의 (ReferenceError 해결)
const client = new Client({ intents: [GatewayIntentBits.Guilds] });

/* ====== DB(JSON) ====== */
const DATA_PATH = path.join(process.cwd(), 'data.json');
function loadDB() {
  if (!fs.existsSync(DATA_PATH)) fs.writeFileSync(DATA_PATH, JSON.stringify({ users:{}, stats:{ total_sold:0 } }, null, 2));
  return JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8'));
}
function saveDB(db) { fs.writeFileSync(DATA_PATH, JSON.stringify(db, null, 2)); }
function getUser(uid) {
  const db = loadDB();
  if (!db.users[uid]) { db.users[uid] = { wallet:0, total:0, count:0, recent:[], roblox:{} }; saveDB(db); }
  return loadDB().users[uid];
}
function setUser(uid, patch) {
  const db = loadDB();
  db.users[uid] = { ...(db.users[uid]||{ wallet:0,total:0,count:0,recent:[],roblox:{} }), ...patch };
  saveDB(db);
}
function pushTxn(uid, amount, desc) {
  const db = loadDB();
  const u = db.users[uid] || { wallet:0,total:0,count:0,recent:[],roblox:{} };
  u.wallet = Math.max(0, (u.wallet||0) + amount);
  if (amount > 0) u.total = (u.total||0) + amount;
  u.count = (u.count||0) + 1;
  u.recent = [{ desc, amount, ts: Date.now() }].concat(u.recent||[]).slice(0,5);
  db.users[uid] = u; saveDB(db);
}

/* ====== 임베드(카드풍) / 컴포넌트 ====== */
const colorPink = 0xff5dd6;
const colorGray = 0x2f3136;

/**
 * 재고 현황을 카드 형태로 표시하는 Embed를 생성합니다. (V2 스타일 반영)
 */
function stockEmbed(title, subtitle, stock, tokens, soldCount, soldAmount, updatedSec, guild) {
  const emb = new EmbedBuilder()
    .setColor(colorPink)
    .setTitle(`## ${title}`) 
    .setDescription(subtitle + `\n\n최종 업데이트: **${updatedSec}초 전**`)
    .addFields(
      // 1개월 부스트 섹션 - inline: true로 나란히 배치하여 카드형 레이아웃
      { name: '### 🎁 1개월 부스트', value: `재고: **${stock['1m'] ?? 0}**개\n토큰: **${tokens['1m'] ?? 0}**개`, inline: true },
      // 2개월 부스트 섹션
      { name: '### ### 🎁 2개월 부스트', value: `재고: **${stock['2m'] ?? 0}**개\n토큰: **${tokens['2m'] ?? 0}**개`, inline: true },
      // 3개월 부스트 섹션
      { name: '### 🎁 3개월 부스트', value: `재고: **${stock['3m'] ?? 0}**개\n토큰: **${tokens['3m'] ?? 0}**개`, inline: true },

      // 판매 현황 섹션
      { name: '\u200B', value: '\u200B', inline: false }, // 줄 바꿈 역할
      { name: '### 📈 판매 현황', value: `거래 횟수: **${soldCount.toLocaleString()}**회`, inline: true },
      { name: '\u200B', value: `누적 판매액: **${soldAmount.toLocaleString()}**원`, inline: true },
      { name: '\u200B', value: '\u200B', inline: true } // 3열 채우기
    )
    .setFooter({ text: 'CopyRight 2025. 최상급 부스트. All rights reserved.' });

  if (guild?.iconURL()) {
    emb.setAuthor({ name: guild.name, iconURL: guild.iconURL() });
  }

  return emb;
}

function panelButtons() {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('p_notice').setStyle(ButtonStyle.Secondary).setLabel('공지사항'),
    new ButtonBuilder().setCustomId('p_charge').setStyle(ButtonStyle.Secondary).setLabel('충전'),
    new ButtonBuilder().setCustomId('p_me').setStyle(ButtonStyle.Secondary).setLabel('내 정보'),
    new ButtonBuilder().setCustomId('p_buy').setStyle(ButtonStyle.Success).setLabel('구매') 
  );
}

function txSelect(stats) {
  const items = stats.recent || [];
  const options = items.length
    ? items.map((e,i)=>({ 
        label:`${e.desc} / ${Number(e.amount).toLocaleString()}원`, 
        value:String(i),
        description: `${new Date(e.ts).toLocaleDateString()} ${new Date(e.ts).toLocaleTimeString()}`
      }))
    : [{ label:'거래 내역 없음', value:'none' }];
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder().setCustomId('tx_select').setPlaceholder('최근 거래내역 보기').addOptions(options)
  );
}

function noticeEmbed(guild) {
  const emb = new EmbedBuilder()
    .setColor(colorGray)
    .setTitle('📢 공지사항')
    .setDescription('<#1419230737244229653> 채널을 필독 부탁드립니다.\n\n필독하지 않아 발생하는 불이익은 책임지지 않습니다.')
    .setFooter({ text: '⚠️ 중요 정보' });
    
  if (guild?.iconURL()) {
    emb.setAuthor({ name: guild.name, iconURL: guild.iconURL() });
  }
  return emb;
}

/**
 * 사용자 정보를 카드 형태로 표시하는 Embed를 생성합니다. (V2 스타일 반영)
 */
function myInfoEmbed(guild, user, stats) {
  const emb = new EmbedBuilder()
    .setColor(colorPink)
    .setTitle(`${user.displayName || user.username}님 정보`)
    .setDescription('현재 계정의 자판기 이용 현황입니다.')
    .addFields(
      // codeBlock으로 금액 정보를 회색 박스(카드)처럼 분리
      { name: '### 💳 보유 금액', value: codeBlock(`${Number(stats.wallet||0).toLocaleString()} 원`), inline: true },
      { name: '### 💰 누적 금액', value: codeBlock(`${Number(stats.total||0).toLocaleString()} 원`), inline: true },
      { name: '### 🛒 거래 횟수', value: codeBlock(`${Number(stats.count||0).toLocaleString()} 회`), inline: true },
      { name: '\u200B', value: '--- **최근 거래내역 5개** ---', inline: false }
    );

  if (user.displayAvatarURL) {
    emb.setThumbnail(user.displayAvatarURL());
  }
  return emb;
}

/* ====== Slash Commands ====== */
const cmdDefs = [
  new SlashCommandBuilder().setName('재고카드').setDescription('카드풍 재고 표시(1장)'),
  new SlashCommandBuilder().setName('재고패널').setDescription('카드풍 재고 2장 연속 표시')
].map(c=>c.toJSON());

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  const rest = new REST({ version:'10' }).setToken(TOKEN);
  try {
    const app = await client.application.fetch();
    if (GUILD_ID) {
      // 길드 명령어 동기화
      await rest.put(Routes.applicationGuildCommands(app.id, GUILD_ID), { body: cmdDefs });
      console.log('[SYNC] guild sync ok', GUILD_ID);
    } else {
      // 글로벌 명령어 동기화
      await rest.put(Routes.applicationCommands(app.id), { body: cmdDefs });
      console.log('[SYNC] global sync ok');
    }
  } catch (e) { console.error('[SYNC] error', e); }
});

client.on('interactionCreate', async (i) => {
  try {
    if (i.isChatInputCommand()) {
      if (i.commandName === '재고카드') {
        const emb = stockEmbed(
          '24시간 자동 자판기',
          '아래 원하시는 버튼을 눌러 이용해주세요',
          { '1m':624, '2m':0, '3m':0 },
          { '1m':312, '2m':0, '3m':0 },
          411, 1200300, 19, i.guild
        );
        // 안정적인 Embed와 ActionRow 전송
        await i.reply({ embeds:[emb], components:[panelButtons()], ephemeral:false });
        return;
      }
      if (i.commandName === '재고패널') {
        const emb1 = stockEmbed('24시간 자동 자판기', '현재 재고 현황입니다.', { '1m':624, '2m':0, '3m':0 }, { '1m':312,'2m':0,'3m':0 }, 411, 1200300, 19, i.guild);
        const emb2 = stockEmbed('부스트 현황(백업)', '보조 재고판', { '1m':120,'2m':32,'3m':4 }, { '1m':60,'2m':16,'3m':2 }, 157, 420000, 5, i.guild);
        // 임베드 2개 + 버튼 1세트 전송
        await i.reply({ embeds:[emb1, emb2], components:[panelButtons()], ephemeral:false });
        return;
      }
    }

    if (i.isButton()) {
      // 버튼 인터랙션은 Embed로 안정적으로 처리
      try { await i.deferUpdate(); } catch {}
      const cid = i.customId;
      
      if (cid === 'p_notice') {
        await i.followUp({ embeds:[noticeEmbed(i.guild)], ephemeral:true });
      } else if (cid === 'p_me') {
        const stats = getUser(i.user.id);
        await i.followUp({ embeds:[myInfoEmbed(i.guild, i.user, stats)], components:[txSelect(stats)], ephemeral:true });
      } else if (cid === 'p_charge') {
        pushTxn(i.user.id, 1000, '충전');
        const stats = getUser(i.user.id);
        await i.followUp({ content:'충전 완료!', embeds:[myInfoEmbed(i.guild, i.user, stats)], components:[txSelect(stats)], ephemeral:true });
      } else if (cid === 'p_buy') {
        pushTxn(i.user.id, -500, '구매');
        const stats = getUser(i.user.id);
        await i.followUp({ content:'구매 처리 완료!', embeds:[myInfoEmbed(i.guild, i.user, stats)], components:[txSelect(stats)], ephemeral:true });
      }
      return;
    }

    if (i.isStringSelectMenu() && i.customId === 'tx_select') {
      try { await i.deferUpdate(); } catch {}
      
      const stats = getUser(i.user.id);
      const selectedIndex = parseInt(i.values[0]);
      
      if (i.values[0] !== 'none' && stats.recent[selectedIndex]) {
        const txn = stats.recent[selectedIndex];
        const txnTime = new Date(txn.ts).toLocaleString();
        const desc = txn.amount > 0 ? '충전' : '구매';
        
        await i.followUp({
          embeds: [
            new EmbedBuilder()
              .setColor(txn.amount > 0 ? ButtonStyle.Success : ButtonStyle.Danger)
              .setTitle(`거래 상세 정보 (${desc})`)
              .addFields(
                { name: '거래 금액', value: `${Number(txn.amount).toLocaleString()} 원`, inline: true },
                { name: '거래 유형', value: txn.desc, inline: true },
                { name: '거래 일시', value: txnTime, inline: false }
              )
              .setFooter({ text: `현재 보유 금액: ${Number(stats.wallet).toLocaleString()} 원` })
          ],
          ephemeral: true
        });
      } else {
        await i.followUp({ content: '선택한 거래 내역이 없거나 유효하지 않습니다.', ephemeral: true });
      }
      return;
    }
  } catch (e) {
    console.error('[INT] error', e);
    // 명령어 타임아웃 방지 및 안정적인 오류 응답
    try { if (!i.replied && !i.deferred) await i.reply({ content:'처리 중 예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.', ephemeral:true }); } catch {}
  }
});

client.login(TOKEN);
