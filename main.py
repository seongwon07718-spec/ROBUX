const { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder } = require('discord.js');
require('dotenv').config();

const TOKEN = process.env.DISCORD_TOKEN;
const GUILD_ID = process.env.GUILD_ID || '';
if (!TOKEN) { console.error('[ENV] DISCORD_TOKEN 누락'); process.exit(1); }

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

/**
 * Components v2 “card” 예시 페이로드 빌더
 * - type: 4 → Components v2 컨테이너
 * - layout: "card"
 * - blocks: 카드 내 블록 요소(헤더/텍스트/배지/버튼/구분선 등)
 * - actions: 각 블록의 인터랙션 id(custom_id)
 */
function buildStockCard({ title, subtitle, stock, tokens, soldCount, soldAmount, updatedSec }) {
  return {
    type: 4,
    layout: 'card',
    blocks: [
      { type: 'header', text: title, icon: { emoji: '📦' }, size: 'lg' },
      { type: 'text', content: subtitle, style: 'muted' },
      { type: 'divider' },
      {
        type: 'stats',
        items: [
          { label: '1개월 부스트', value: `${stock['1m'] ?? 0} Boosts`, hint: `${tokens['1m'] ?? 0} Tokens`, color: 'indigo' },
          { label: '2개월 부스트', value: `${stock['2m'] ?? 0} Boosts`, hint: `${tokens['2m'] ?? 0} Tokens`, color: 'blue' },
          { label: '3개월 부스트', value: `${stock['3m'] ?? 0} Boosts`, hint: `${tokens['3m'] ?? 0} Tokens`, color: 'violet' },
        ],
      },
      { type: 'divider' },
      {
        type: 'stats',
        items: [
          { label: '판매 횟수', value: `${soldCount.toLocaleString()}회`, color: 'green' },
          { label: '총 매출', value: `${soldAmount.toLocaleString()}원`, color: 'green' },
        ],
      },
      { type: 'spacer', size: 'sm' },
      { type: 'text', content: `업데이트: ${updatedSec}초 전`, style: 'muted' },
      { type: 'divider' },
      {
        type: 'actions',
        items: [
          { type: 'button', style: 'secondary', label: '공지사항', action_id: 'card_notice' },
          { type: 'button', style: 'secondary', label: '내 정보', action_id: 'card_me' },
        ],
      },
      { type: 'footer', text: 'CopyRight 2025. 최상급 부스트. All rights reserved.' },
    ],
  };
}

function buildDualCards() {
  const left = buildStockCard({
    title: '최상급 부스트',
    subtitle: '현재 재고 현황입니다.',
    stock: { '1m': 624, '2m': 0, '3m': 0 },
    tokens: { '1m': 312, '2m': 0, '3m': 0 },
    soldCount: 411,
    soldAmount: 1200300,
    updatedSec: 19,
  });
  const right = buildStockCard({
    title: '부스트 현황(백업)',
    subtitle: '보조 재고판',
    stock: { '1m': 120, '2m': 32, '3m': 4 },
    tokens: { '1m': 60, '2m': 16, '3m': 2 },
    soldCount: 157,
    soldAmount: 420000,
    updatedSec: 5,
  });
  return {
    type: 4,
    layout: 'board', // 가로 2분할 카드 레이아웃
    columns: 2,
    items: [left, right],
  };
}

/* 슬래시 명령 정의 */
const commands = [
  new SlashCommandBuilder().setName('재고카드').setDescription('컴포넌트 v2 카드로 재고 표시(1장)'),
  new SlashCommandBuilder().setName('재고패널').setDescription('컴포넌트 v2 카드 2장 그리드'),
].map(c => c.toJSON());

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  const rest = new REST({ version: '10' }).setToken(TOKEN);
  try {
    if (GUILD_ID) {
      await rest.put(
        Routes.applicationGuildCommands((await client.application.fetch()).id, GUILD_ID),
        { body: commands },
      );
      console.log('[SYNC] guild sync ok', GUILD_ID);
    } else {
      await rest.put(Routes.applicationCommands((await client.application.fetch()).id), { body: commands });
      console.log('[SYNC] global sync ok');
    }
  } catch (e) { console.error('[SYNC] error', e); }
});

client.on('interactionCreate', async (i) => {
  try {
    // 슬래시: 안내문 없이 즉시 카드 보냄
    if (i.isChatInputCommand()) {
      if (i.commandName === '재고카드') {
        const payload = buildStockCard({
          title: '최상급 부스트',
          subtitle: '현재 재고 현황입니다.',
          stock: { '1m': 624, '2m': 0, '3m': 0 },
          tokens: { '1m': 312, '2m': 0, '3m': 0 },
          soldCount: 411, soldAmount: 1200300, updatedSec: 19,
        });
        await i.reply({ components: [payload], ephemeral: false }); // v2카드는 components 배열로 전송
        return;
      }
      if (i.commandName === '재고패널') {
        const board = buildDualCards();
        await i.reply({ components: [board], ephemeral: false });
        return;
      }
    }

    // 버튼/액션: deferUpdate → followUp(ephemeral)
    // Components v2 버튼 클릭은 i.isMessageComponent()로 들어오며, customId는 action_id가 매핑됨
    if (i.isMessageComponent()) {
      try { await i.deferUpdate(); } catch {}
      const cid = i.customId;

      if (cid === 'card_notice') {
        await i.followUp({
          ephemeral: true,
          components: [{
            type: 4,
            layout: 'card',
            blocks: [
              { type: 'header', text: '공지사항', icon: { emoji: '📣' } },
              { type: 'text', content: '<#1419230737244229653> 필독 부탁드립니다', style: 'default' },
            ],
          }],
        });
      } else if (cid === 'card_me') {
        const stats = getUser(i.user.id);
        await i.followUp({
          ephemeral: true,
          components: [{
            type: 4,
            layout: 'card',
            blocks: [
              { type: 'header', text: `${i.user.displayName || i.user.username}님 정보`, icon: { emoji: '👤' } },
              { type: 'profile', user_id: i.user.id, align: 'right' },
              { type: 'text', content: `### 보유 금액 : ${Number(stats.wallet||0).toLocaleString()}`, style: 'default' },
              { type: 'text', content: `### 누적 금액 : ${Number(stats.total||0).toLocaleString()}`, style: 'default' },
              { type: 'text', content: `### 거래 횟수 : ${Number(stats.count||0).toLocaleString()}`, style: 'default' },
              { type: 'divider' },
              {
                type: 'select',
                action_id: 'tx_select',
                placeholder: '거래내역 보기',
                options: (stats.recent||[]).slice(0,5).map((e,idx)=>({
                  label: `${e.desc} / ${Number(e.amount).toLocaleString()}`, value: String(idx),
                })) || [{ label:'거래 내역 없음', value:'none' }],
              },
            ],
          }],
        });
      } else if (cid === 'tx_select') {
        // 드롭다운 선택은 조용히 처리
        // 선택 항목 i.values 사용 가능. 화면 변경 없이 종료
      }
      return;
    }
  } catch (e) {
    console.error('[INT] error', e);
    try { if (!i.replied) await i.reply({ content: '에러가 났어. 잠시 후 다시 시도해줘.', ephemeral: true }); } catch {}
  }
});

client.login(TOKEN);
