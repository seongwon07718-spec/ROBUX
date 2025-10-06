require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  MessageFlags,
  TextDisplayBuilder,
  ContainerBuilder,
  SectionBuilder,
  SeparatorBuilder,
  ButtonBuilder,
  ButtonStyle,
} = require('discord.js');

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

// .env 필수: DISCORD_TOKEN
// 옵션: GUILD_ID(있으면 길드만), APP_ID(없으면 런타임 봇 ID 사용)
const TOKEN = process.env.DISCORD_TOKEN;
const GUILD_ID = process.env.GUILD_ID || '';
let APP_ID = process.env.APP_ID || '';

const commands = [
  { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
];

client.once('ready', async (c) => {
  console.log(`${c.user.username} is online.`);
  const rest = new REST({ version: '10' }).setToken(TOKEN);
  if (!APP_ID) APP_ID = c.user.id;

  try {
    // 0) 전역/길드 둘 다 한 번 싹 비우기(중복 완전 제거)
    await rest.put(Routes.applicationCommands(APP_ID), { body: [] }).catch(() => {});
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(APP_ID, GUILD_ID), { body: [] }).catch(() => {});
    }

    // 1) 선택: 길드만 등록 or 전역만 등록
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(APP_ID, GUILD_ID), { body: commands });
      console.log('길드 커맨드 등록 완료(즉시 반영): /로벅스패널');
    } else {
      await rest.put(Routes.applicationCommands(APP_ID), { body: commands });
      console.log('전역 커맨드 등록 완료(반영 몇 분 소요): /로벅스패널');
    }
  } catch (err) {
    console.error('커맨드 초기화/등록 실패:', err);
  }
});

client.on('interactionCreate', async (interaction) => {
  if (interaction.isChatInputCommand()) {
    if (interaction.commandName !== '로벅스패널') return;

    // 상단 섹션
    const topText = new TextDisplayBuilder().setContent(
      '자동화 로벅스\n아래 버튼을 눌러 이용해주세요\n자충 오류 문의는 문의하기'
    );
    const sectionTop = new SectionBuilder().addTextDisplayComponents(topText);

    // 막대기(간격 좁게)
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
    if (typeof sectionStock.setButtonAccessory === 'function') {
      sectionStock = sectionStock.setButtonAccessory(stockBtn);
    } else if (typeof sectionStock.setButtonAccessories === 'function') {
      sectionStock = sectionStock.setButtonAccessories([stockBtn]);
    } else {
      console.warn('섹션 버튼 액세서리 메서드가 없음. 빌드 문서 확인 필요');
    }

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
    if (typeof sectionSales.setButtonAccessory === 'function') {
      sectionSales = sectionSales.setButtonAccessory(salesBtn);
    } else if (typeof sectionSales.setButtonAccessories === 'function') {
      sectionSales = sectionSales.setButtonAccessories([salesBtn]);
    }

    // 중간 막대기
    const sepMid = new SeparatorBuilder().setSpacing('Small');

    // 하단 2x2(회색, 활성) — 섹션 4개로 분리(섹션당 버튼 1개)
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
    let sectionBtnInfo   = new SectionBuilder();
    let sectionBtnBuy    = new SectionBuilder();

    // 단일/배열 메서드 둘 다 대응
    if (typeof sectionBtnNotice.setButtonAccessory === 'function') {
      sectionBtnNotice = sectionBtnNotice.setButtonAccessory(noticeBtn);
      sectionBtnCharge = sectionBtnCharge.setButtonAccessory(chargeBtn);
      sectionBtnInfo   = sectionBtnInfo.setButtonAccessory(infoBtn);
      sectionBtnBuy    = sectionBtnBuy.setButtonAccessory(buyBtn);
    } else if (typeof sectionBtnNotice.setButtonAccessories === 'function') {
      sectionBtnNotice = sectionBtnNotice.setButtonAccessories([noticeBtn]);
      sectionBtnCharge = sectionBtnCharge.setButtonAccessories([chargeBtn]);
      sectionBtnInfo   = sectionBtnInfo.setButtonAccessories([infoBtn]);
      sectionBtnBuy    = sectionBtnBuy.setButtonAccessories([buyBtn]);
    }

    // 하단 막대기
    const sepBottom = new SeparatorBuilder().setSpacing('Small');

    // 푸터 섹션
    const footerText = new TextDisplayBuilder().setContent('자동화 로벅스 / 2025 / GMT+09:00');
    const sectionFooter = new SectionBuilder().addTextDisplayComponents(footerText);

    // 컨테이너 조립
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
    return;
  }

  // 2x2 버튼 눌러도 화면 반응 배너 안 뜨게 묵음 처리
  if (interaction.isButton()) {
    try { await interaction.deferUpdate(); } catch (_) {}
  }
});

client.login(TOKEN);
