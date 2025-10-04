const { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder, ComponentType } = require('discord.js');
// discord.js에서 MessageFlags는 MessageType이므로, V2 플래그는 수동으로 처리합니다.
const COMPONENTS_V2_FLAG = 1 << 15; 

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

// ----------------------------------------------------
// Component V2 (Display Components) API 구조체 생성 함수
// ----------------------------------------------------

/**
 * Components V2 스타일의 재고 카드를 JSON 구조체로 반환합니다.
 */
function stockV2Components(title, subtitle, stock, tokens, soldCount, soldAmount, updatedSec) {
    const formatCount = (count) => `**${count ?? 0}**`;

    // 섹션 컴포넌트를 사용한 재고 정보 (2열 레이아웃 모방)
    const stockContainer = {
        type: 6, // CONTAINER
        components: [
            // 1개월 부스트
            { type: 5, components: [ // SECTION
                { type: 1, content: `### 🎁 1개월 부스트\n재고: ${formatCount(stock['1m'])}개 | 토큰: ${formatCount(tokens['1m'])}개` }
            ]},
            // 2개월 부스트
            { type: 5, components: [ // SECTION
                { type: 1, content: `### 🎁 2개월 부스트\n재고: ${formatCount(stock['2m'])}개 | 토큰: ${formatCount(tokens['2m'])}개` }
            ]},
            // 3개월 부스트
            { type: 5, components: [ // SECTION
                { type: 1, content: `### 🎁 3개월 부스트\n재고: ${formatCount(stock['3m'])}개 | 토큰: ${formatCount(tokens['3m'])}개` }
            ]},
        ],
    };

    // 판매 현황 섹션
    const statsSection = {
        type: 5, // SECTION
        components: [
            { type: 1, content: `### 📈 판매 현황\n거래 횟수: **${soldCount.toLocaleString()}**회\n누적 판매액: **${soldAmount.toLocaleString()}**원` }
        ]
    };

    // Footer 섹션
    const footerSection = {
        type: 5, // SECTION
        components: [
             { type: 1, content: `업데이트: **${updatedSec}초 전**\n\n\`CopyRight 2025. 최상급 부스트. All rights reserved.\`` }
        ]
    };
    
    // 전체 메시지 구조
    return [
        { type: 1, content: `## ${title}\n${subtitle}` }, // TEXT_DISPLAY (Title)
        { type: 2, spacing: 3 }, // SEPARATOR
        stockContainer,
        { type: 2, spacing: 3 }, // SEPARATOR
        statsSection,
        { type: 2, spacing: 3 }, // SEPARATOR
        footerSection
    ];
}

/**
 * 사용자 정보 카드를 JSON 구조체로 반환합니다.
 */
function myInfoV2Components(user, stats) {
    const avatarUrl = user.displayAvatarURL ? user.displayAvatarURL() : null;

    // 통계 정보 섹션 (3열 레이아웃 모방)
    const walletSection = { type: 5, components: [ { type: 1, content: `### 💳 보유 금액\n\`${Number(stats.wallet||0).toLocaleString()} 원\`` } ] };
    const totalSection = { type: 5, components: [ { type: 1, content: `### 💰 누적 금액\n\`${Number(stats.total||0).toLocaleString()} 원\`` } ] };
    const countSection = { type: 5, components: [ { type: 1, content: `### 🛒 거래 횟수\n\`${Number(stats.count||0).toLocaleString()} 회\`` } ] };

    return [
        { type: 1, content: `## ${user.displayName || user.username}님 정보` }, // TEXT_DISPLAY (Title)
        { 
            type: 5, // SECTION
            components: [
                { type: 1, content: '현재 계정의 자판기 이용 현황입니다.' }, // TEXT_DISPLAY
                ...(avatarUrl ? [{ type: 4, url: avatarUrl, alt_text: 'Avatar' }] : []) // THUMBNAIL (있는 경우)
            ]
        },
        { type: 2, spacing: 3 }, // SEPARATOR
        { 
            type: 6, // CONTAINER (통계 정보)
            components: [walletSection, totalSection, countSection]
        },
        { type: 2, spacing: 3 }, // SEPARATOR
        { type: 1, content: '--- **최근 거래내역 5개** ---' }
    ];
}


// 기존 버튼 컴포넌트는 ActionRowBuilder로 생성 가능
function panelButtons() {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('p_notice').setStyle(ButtonStyle.Secondary).setLabel('공지사항'),
    new ButtonBuilder().setCustomId('p_charge').setStyle(ButtonStyle.Secondary).setLabel('충전'),
    new ButtonBuilder().setCustomId('p_me').setStyle(ButtonStyle.Secondary).setLabel('내 정보'),
    new ButtonBuilder().setCustomId('p_buy').setStyle(ButtonStyle.Success).setLabel('구매') 
  );
}

// 기존 SelectMenu는 ActionRowBuilder로 생성 가능
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

// 공지 V2 컴포넌트
function noticeV2Components() {
    return [
        { type: 1, content: '## 📢 공지사항' },
        { type: 1, content: '### <#1419230737244229653> 채널 필독 부탁드립니다.\n\n필독하지 않아 발생하는 불이익은 책임지지 않습니다.' },
        { type: 2, spacing: 3 }, // SEPARATOR
        { type: 1, content: '⚠️ 중요 정보' }
    ];
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
      await rest.put(Routes.applicationGuildCommands(app.id, GUILD_ID), { body: cmdDefs });
      console.log('[SYNC] guild sync ok', GUILD_ID);
    } else {
      await rest.put(Routes.applicationCommands(app.id), { body: cmdDefs });
      console.log('[SYNC] global sync ok');
    }
  } catch (e) { console.error('[SYNC] error', e); }
});

client.on('interactionCreate', async (i) => {
  try {
    if (i.isChatInputCommand()) {
      if (i.commandName === '재고카드') {
        const v2_components = stockV2Components(
          '24시간 자동 자판기',
          '아래 원하시는 버튼을 눌러 이용해주세요',
          { '1m':624, '2m':0, '3m':0 },
          { '1m':312, '2m':0, '3m':0 },
          411, 1200300, 19
        );
        // V2 컴포넌트와 버튼을 함께 전송
        await i.reply({ components: v2_components.concat(panelButtons().toJSON()), flags: COMPONENTS_V2_FLAG, ephemeral:false });
        return;
      }
      if (i.commandName === '재고패널') {
        const v2_components1 = stockV2Components('24시간 자동 자판기', '현재 재고 현황입니다.', { '1m':624, '2m':0, '3m':0 }, { '1m':312,'2m':0,'3m':0 }, 411, 1200300, 19);
        const v2_components2 = stockV2Components('부스트 현황(백업)', '보조 재고판', { '1m':120,'2m':32,'3m':4 }, { '1m':60,'2m':16,'3m':2 }, 157, 420000, 5);
        
        // 두 개의 V2 컴포넌트 세트를 합쳐 전송
        const all_components = v2_components1.concat([{ type: 2, spacing: 5 }]).concat(v2_components2); // 구분선 추가
        
        await i.reply({ components: all_components.concat(panelButtons().toJSON()), flags: COMPONENTS_V2_FLAG, ephemeral:false });
        return;
      }
    }

    // 버튼 인터랙션 (기존 ActionRowBuilder와 ButtonBuilder 사용)
    if (i.isButton()) {
      try { await i.deferUpdate(); } catch {}
      const cid = i.customId;
      
      if (cid === 'p_notice') {
        const v2_components = noticeV2Components();
        await i.followUp({ components: v2_components, flags: COMPONENTS_V2_FLAG, ephemeral:true });
      } else if (cid === 'p_me') {
        const stats = getUser(i.user.id);
        const v2_components = myInfoV2Components(i.user, stats);
        // 내 정보 V2 컴포넌트와 SelectMenu 버튼을 함께 전송
        await i.followUp({ components: v2_components.concat(txSelect(stats).toJSON()), flags: COMPONENTS_V2_FLAG, ephemeral:true });
      } else if (cid === 'p_charge') {
        pushTxn(i.user.id, 1000, '충전');
        const stats = getUser(i.user.id);
        const v2_components = myInfoV2Components(i.user, stats);
        await i.followUp({ content:'충전 완료!', components: v2_components.concat(txSelect(stats).toJSON()), flags: COMPONENTS_V2_FLAG, ephemeral:true });
      } else if (cid === 'p_buy') {
        pushTxn(i.user.id, -500, '구매');
        const stats = getUser(i.user.id);
        const v2_components = myInfoV2Components(i.user, stats);
        await i.followUp({ content:'구매 처리 완료!', components: v2_components.concat(txSelect(stats).toJSON()), flags: COMPONENTS_V2_FLAG, ephemeral:true });
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
        
        // 거래 내역 상세 정보는 임베드로 빠르게 표시
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
    console.error('[INT] Component V2 error', e);
    try { 
        if (!i.replied && !i.deferred) {
            await i.reply({ content:'**[V2 오류]** 컴포넌트 V2 처리 중 에러가 발생했습니다. 잠시 후 다시 시도하거나, 서버 관리자에게 문의하세요.', ephemeral:true }); 
        }
    } catch {}
  }
});

client.login(TOKEN);
