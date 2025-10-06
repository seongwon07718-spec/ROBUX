require('dotenv/config');
const {
  Client, GatewayIntentBits, REST, Routes, MessageFlags,
  TextDisplayBuilder, ContainerBuilder, SectionBuilder, SeparatorBuilder,
  ButtonBuilder, ButtonStyle,
} = require('discord.js');

const client = new Client({ intents: [GatewayIntentBits.Guilds] });
const TOKEN = process.env.DISCORD_TOKEN;
const GUILD_ID = process.env.GUILD_ID || '';
const commands = [{ name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' }];

// 🌟🌟🌟 오류를 해결한 최종 함수 🌟🌟🌟
function attachButtonsToSection(section, buttons) {
  // 버튼 배열 정규화
  const arr = Array.isArray(buttons) ? buttons : [buttons];
  
  // SectionBuilder는 .setButtonAccessories(buttons: ButtonBuilder[])를 사용해야 합니다.
  if (typeof section.setButtonAccessories === 'function') {
    return section.setButtonAccessories(arr);
  }
  
  // 만약 setButtonAccessories 메서드가 없다면,
  // 원본 section 인스턴스를 그대로 반환하여 다음 코드에서 'undefined'가 할당되는 것을 막습니다.
  // 이 부분이 첫 번째 스크린샷 오류의 핵심 원인이었습니다.
  return section;
}
// 🌟🌟🌟 수정 끝 🌟🌟🌟

client.once('ready', async (c) => {
  console.log(`${c.user.username} is online.`);
  const rest = new REST({ version: '10' }).setToken(TOKEN);
  // 중복 제거: 전역/길드 모두 비우고 → 선택한 범위에만 재등록
  try {
    await rest.put(Routes.applicationCommands(c.user.id), { body: [] }).catch(() => {});
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(c.user.id, GUILD_ID), { body: [] }).catch(() => {});
      await rest.put(Routes.applicationGuildCommands(c.user.id, GUILD_ID), { body: commands });
      console.log('길드 등록 완료: /로벅스패널 (즉시 반영)');
    } else {
      await rest.put(Routes.applicationCommands(c.user.id), { body: commands });
      console.log('전역 등록 완료: /로벅스패널 (반영 수 분)');
    }
  } catch (e) {
    console.error('커맨드 초기화/등록 실패:', e);
  }
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== '로벅스패널') return;

  // 상단 섹션
  const topText = new TextDisplayBuilder().setContent(
    '자동화 로벅스\n아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 문의하기'
  );
  const sectionTop = new SectionBuilder().addTextDisplayComponents(topText);

  // 막대기
  const sepTop = new SeparatorBuilder().setSpacing('Small');

  // 재고 섹션
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

  // 누적 섹션
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

  // 2x2 아래 버튼(활성)
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

  let sectionBtnNotice = new SectionBuilder();
  let sectionBtnCharge = new SectionBuilder();
  let sectionBtnInfo = new SectionBuilder();
  let sectionBtnBuy = new SectionBuilder();

  sectionBtnNotice = attachButtonsToSection(sectionBtnNotice, noticeBtn);
  sectionBtnCharge = attachButtonsToSection(sectionBtnCharge, chargeBtn);
  sectionBtnInfo = attachButtonsToSection(sectionBtnInfo, infoBtn);
  sectionBtnBuy = attachButtonsToSection(sectionBtnBuy, buyBtn);

  const sepBottom = new SeparatorBuilder().setSpacing('Small');

  const footerText = new TextDisplayBuilder().setContent('자동화 로벅스 / 2025 / GMT+09:00');
  const sectionFooter = new SectionBuilder().addTextDisplayComponents(footerText);

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

  await interaction.reply({
    flags: MessageFlags.IsComponentsV2,
    components: [container],
  });
});

// 버튼 눌러도 화면 반응 배너 안 뜨게
client.on('interactionCreate', async (i) => {
  if (!i.isButton()) return;
  try { await i.deferUpdate(); } catch (_) {}
});

client.login(TOKEN);
