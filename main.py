Require('dotenv/config');
const {
  Client, GatewayIntentBits, REST, Routes, MessageFlags,
  TextDisplayBuilder, ContainerBuilder, SectionBuilder, SeparatorBuilder,
  ButtonBuilder, ButtonStyle,
} = require('discord.js');

const client = new Client({ intents: [GatewayIntentBits.Guilds] });
const TOKEN = process.env.DISCORD_TOKEN;
const GUILD_ID = process.env.GUILD_ID || '';
const commands = [{ name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' }];

// 🌟🌟🌟 이 함수를 아래와 같이 수정했습니다 🌟🌟🌟
function attachButtonsToSection(section, buttons) {
  // 버튼 배열 정규화
  const arr = Array.isArray(buttons) ? buttons : [buttons];
  
  // SectionBuilder는 .setButtonAccessories(buttons: ButtonBuilder[])를 사용해야 합니다.
  // 이 함수가 최종적으로 SectionBuilder 인스턴스를 반환하도록 보장합니다.
  if (typeof section.setButtonAccessories === 'function') {
    return section.setButtonAccessories(arr);
  }
  
  // 이전 버전의 Discord.js 호환을 시도할 때 발생할 수 있는 오류를 방지하기 위해
  // 다른 모든 로직을 제거하고, 가장 호환되는 setButtonAccessories만 남깁니다.
  
  // 만약 setButtonAccessories가 없다면 오류를 던지지만,
  // discord.js v14 환경에서는 이것이 유효한 메서드이거나
  // SectionBuilder를 반환하는 다른 메서드여야 합니다.
  
  // setAccessories({ buttons: arr })와 같은 다른 메서드가 필요하다면,
  // 이는 사용자가 설치한 discord.js/discord-components-v2 버전의 문제입니다.
  
  // 여기서는 가장 유력한 setButtonAccessories를 사용하고,
  // 만약 함수가 없으면 원본 섹션을 반환하여 코드가 크래시되는 것을 방지합니다.
  console.warn('경고: setButtonAccessories 메서드를 찾지 못했습니다. 원본 Section을 반환합니다.');
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

// ... (나머지 코드는 동일)

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

  // 🌟🌟🌟 attachButtonsToSection 함수는 섹션 인스턴스를 반환합니다 🌟🌟🌟
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
