const {
  MessageFlags,
  Client,
  GatewayIntentBits,
  ButtonBuilder,
  ButtonStyle,
} = require('discord.js');

// 컨테이너/섹션/텍스트/구분선은 @discordjs/builders에서 임포트
const {
  ContainerBuilder,
  SectionBuilder,
  TextDisplayBuilder,
  SeparatorBuilder,
} = require('@discordjs/builders');

// 섹션에 버튼 액세서리 붙이는 헬퍼(빌드별 메서드 자동 매칭)
function attachButtonsToSection(section, buttons) {
  const arr = Array.isArray(buttons) ? buttons : [buttons];
  if (typeof section.setLayout === 'function') {
    try { section.setLayout('withButtonAccessory'); } catch (_) {}
  }
  if (typeof section.setButtonAccessory === 'function' && arr.length === 1) return section.setButtonAccessory(arr[0]);
  if (typeof section.setButtonAccessories === 'function') return section.setButtonAccessories(arr);
  if (typeof section.addButtonAccessories === 'function') return section.addButtonAccessories(arr);
  if (typeof section.setAccessories === 'function') return section.setAccessories({ buttons: arr });
  throw new Error('이 빌드에서 섹션 버튼 액세서리 메서드를 찾지 못했어');
}

function buildContainer() {
  // 상단 안내
  const top = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 문의하기'
  );
  const sectionTop = new SectionBuilder().addTextDisplayComponents(top);

  const sepTop = new SeparatorBuilder().setSpacing('Small');

  // 재고 섹션 + 핑크 비활성 버튼
  const stockText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n60초마다 갱신됩니다'
  );
  const stockBtn = new ButtonBuilder()
    .setCustomId('stock_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);
  let sectionStock = new SectionBuilder().addTextDisplayComponents(stockText);
  sectionStock = attachButtonsToSection(sectionStock, stockBtn);

  // 누적 섹션 + 핑크 비활성 버튼
  const salesText = new TextDisplayBuilder().setContent(
    '** <a:upuoipipi:1423892277373304862>누적 판매량**\n총 판매된 로벅스'
  );
  const salesBtn = new ButtonBuilder()
    .setCustomId('sales_zero')
    .setLabel('0로벅스')
    .setStyle(ButtonStyle.Danger)
    .setDisabled(true);
  let sectionSales = new SectionBuilder().addTextDisplayComponents(salesText);
  sectionSales = attachButtonsToSection(sectionSales, salesBtn);

  const sepMid = new SeparatorBuilder().setSpacing('Small');

  // 하단 2x2(회색, 활성)
  const noticeBtn = new ButtonBuilder()
    .setCustomId('notice')
    .setEmoji({ name: 'emoji_5', id: '1424003478275231916' })
    .setLabel('공지사항')
    .setStyle(ButtonStyle.Secondary);

  const chargeBtn = new ButtonBuilder()
    .setCustomId('charge')
    .setEmoji({ name: 'charge', id: '1424003480007475281' })
    .setLabel('충전')
    .setStyle(ButtonStyle.Secondary);

  const infoBtn = new ButtonBuilder()
    .setCustomId('info')
    .setEmoji({ name: 'info', id: '1424003482247237908' })
    .setLabel('내 정보')
    .setStyle(ButtonStyle.Secondary);

  const buyBtn = new ButtonBuilder()
    .setCustomId('buy')
    .setEmoji({ name: 'category', id: '1424003481240469615' })
    .setLabel('구매')
    .setStyle(ButtonStyle.Secondary);

  // 섹션 4개(섹션당 버튼 1개 → 검증 안전)
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

  const container = new ContainerBuilder()
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

  return container;
}

function bindInteractions(client) {
  client.on('interactionCreate', async (interaction) => {
    // 패널 명령
    if (interaction.isChatInputCommand() && interaction.commandName === '로벅스패널') {
      const container = buildContainer();
      await interaction.reply({
        flags: MessageFlags.IsComponentsV2,
        components: [container],
      });
      return;
    }

    // 하단 2x2 버튼은 눌러도 화면 반응 배너 안 뜨게
    if (interaction.isButton()) {
      try { await interaction.deferUpdate(); } catch (_) {}
    }
  });
}

module.exports = { bindInteractions };
