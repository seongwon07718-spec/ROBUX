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

- src/panel.js
'use strict';
const { MessageFlags, ButtonBuilder, ButtonStyle } = require('discord.js');
const { ContainerBuilder, SectionBuilder, TextDisplayBuilder, SeparatorBuilder } = require('@discordjs/builders');

function attachButtonsToSection(section, buttons) {
  const arr = Array.isArray(buttons) ? buttons : [buttons];
  if (typeof section.setLayout === 'function') { try { section.setLayout('withButtonAccessory'); } catch (_) {} }
  if (typeof section.setButtonAccessory === 'function' && arr.length === 1) return section.setButtonAccessory(arr[0]);
  if (typeof section.setButtonAccessories === 'function') return section.setButtonAccessories(arr);
  if (typeof section.addButtonAccessories === 'function') return section.addButtonAccessories(arr);
  if (typeof section.setAccessories === 'function') return section.setAccessories({ buttons: arr });
  throw new Error('섹션 버튼 액세서리 메서드를 찾지 못했어');
}

function buildContainer() {
  const top = new TextDisplayBuilder().setContent('자동화 로벅스\n아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 문의하기');
  const sectionTop = new SectionBuilder().addTextDisplayComponents(top);
  const sepTop = new SeparatorBuilder().setSpacing('Small');

  const stockText = new TextDisplayBuilder().setContent('** <a:upuoipipi:1423892277373304862>로벅스 재고**\n60초마다 갱신됩니다');
  const stockBtn = new ButtonBuilder().setCustomId('stock_zero').setLabel('0로벅스').setStyle(ButtonStyle.Danger).setDisabled(true);
  let sectionStock = new SectionBuilder().addTextDisplayComponents(stockText);
  sectionStock = attachButtonsToSection(sectionStock, stockBtn);

  const salesText = new TextDisplayBuilder().setContent('** <a:upuoipipi:1423892277373304862>누적 판매량**\n총 판매된 로벅스');
  const salesBtn = new ButtonBuilder().setCustomId('sales_zero').setLabel('0로벅스').setStyle(ButtonStyle.Danger).setDisabled(true);
  let sectionSales = new SectionBuilder().addTextDisplayComponents(salesText);
  sectionSales = attachButtonsToSection(sectionSales, salesBtn);

  const sepMid = new SeparatorBuilder().setSpacing('Small');

  const noticeBtn = new ButtonBuilder().setCustomId('notice').setEmoji({ name: 'emoji_5', id: '1424003478275231916' }).setLabel('공지사항').setStyle(ButtonStyle.Secondary);
  const chargeBtn = new ButtonBuilder().setCustomId('charge').setEmoji({ name: 'charge', id: '1424003480007475281' }).setLabel('충전').setStyle(ButtonStyle.Secondary);
  const infoBtn   = new ButtonBuilder().setCustomId('info').setEmoji({ name: 'info', id: '1424003482247237908' }).setLabel('내 정보').setStyle(ButtonStyle.Secondary);
  const buyBtn    = new ButtonBuilder().setCustomId('buy').setEmoji({ name: 'category', id: '1424003481240469615' }).setLabel('구매').setStyle(ButtonStyle.Secondary);

  let sectionBtnNotice = new SectionBuilder();
  let sectionBtnCharge = new SectionBuilder();
  let sectionBtnInfo   = new SectionBuilder();
  let sectionBtnBuy    = new SectionBuilder();

  sectionBtnNotice = attachButtonsToSection(sectionBtnNotice, noticeBtn);
  sectionBtnCharge = attachButtonsToSection(sectionBtnCharge, chargeBtn);
  sectionBtnInfo   = attachButtonsToSection(sectionBtnInfo, infoBtn);
  sectionBtnBuy    = attachButtonsToSection(sectionBtnBuy, buyBtn);

  const sepBottom = new SeparatorBuilder().setSpacing('Small');
  const footer = new TextDisplayBuilder().setContent('자동화 로벅스 / 2025 / GMT+09:00');
  const sectionFooter = new SectionBuilder().addTextDisplayComponents(footer);

  return new ContainerBuilder()
    .addSectionComponents(sectionTop)
    .addSeparatorComponents(sepTop)
    .addSectionComponents(sectionStock)
    .addSectionComponents(sectionSales)
    .addSeparatorComponents(sepMid)
    .addSectionComponents(sectionBtnNotice)
    .addSectionComponents(sectionBtnCharge)
    .addSectionComponents(sectionBtnInfo)
    .addSectionComponents(sectionBtnBuy)
    .addSeparatorComponents(sepBottom)
    .addSectionComponents(sectionFooter);
}

function bindInteractions(client) {
  client.on('interactionCreate', async (interaction) => {
    if (interaction.isChatInputCommand() && interaction.commandName === '로벅스패널') {
      await interaction.reply({ flags: MessageFlags.IsComponentsV2, components: [buildContainer()] });
      return;
    }
    if (interaction.isButton()) {
      try { await interaction.deferUpdate(); } catch (_) {}
    }
  });
}
module.exports = { bindInteractions };
