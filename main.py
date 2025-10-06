require('dotenv/config');
const {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  MessageFlags,
  // components-v2 확장 빌드 기준
  TextDisplayBuilder,
  ContainerBuilder,
  SectionBuilder,
  SeparatorBuilder,
  ButtonBuilder,
  ButtonStyle,
} = require('discord.js');

const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

// 즉시 테스트용 길드 등록. .env에 GUILD_ID가 없으면 전역 등록으로 자동 전환됨.
const GUILD_ID = process.env.GUILD_ID || '';

const commands = [
  { name: '로벅스패널', description: '자동화 로벅스 패널을 표시합니다.' },
];

client.once('ready', async (c) => {
  console.log(`${c.user.username} is online.`);
  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);

  try {
    if (GUILD_ID) {
      await rest.put(Routes.applicationGuildCommands(c.user.id, GUILD_ID), { body: commands });
      console.log('길드 커맨드 등록 완료(즉시 반영): /로벅스패널');
    } else {
      await rest.put(Routes.applicationCommands(c.user.id), { body: commands });
      console.log('전역 커맨드 등록 완료(반영까지 수 분): /로벅스패널');
    }
  } catch (err) {
    console.error('커맨드 등록 실패:', err);
  }
});

client.on('interactionCreate', async (interaction) => {
  if (interaction.isChatInputCommand()) {
    if (interaction.commandName !== '로벅스패널') return;

    // 1) 상단 안내 섹션
    const topText = new TextDisplayBuilder().setContent(
      '자동화 로벅스\n' +
      '아래 버튼을 눌러 이용해주세요\n' +
      '자충 오류 문의는 문의하기'
    );
    const sectionTop = new SectionBuilder().addTextDisplayComponents(topText);

    // 2) 긴 막대기(간격 좁게)
    const sepTop = new SeparatorBuilder().setSpacing('Small');

    // 3) 재고 섹션 + 핑크 비활성 버튼
    const stockText = new TextDisplayBuilder().setContent(
      '** <a:upuoipipi:1423892277373304862>로벅스 재고**\n' +
      '60초마다 갱신됩니다'
    );
    const stockBtn = new ButtonBuilder()
      .setCustomId('stock_zero')
      .setLabel('0로벅스')
      .setStyle(ButtonStyle.Danger) // 핑크 톤
      .setDisabled(true); // 못 누르게
    const sectionStock = new SectionBuilder()
      .addTextDisplayComponents(stockText)
      .setButtonAccessory(stockBtn);

    // 4) 누적 판매량 섹션 + 핑크 비활성 버튼
    const salesText = new TextDisplayBuilder().setContent(
      '** <a:upuoipipi:1423892277373304862>누적 판매량**\n' +
      '총 판매된 로벅스'
    );
    const salesBtn = new ButtonBuilder()
      .setCustomId('sales_zero')
      .setLabel('0로벅스')
      .setStyle(ButtonStyle.Danger)
      .setDisabled(true);
    const sectionSales = new SectionBuilder()
      .addTextDisplayComponents(salesText)
      .setButtonAccessory(salesBtn);

    // 5) 중간 긴 막대기
    const sepMid = new SeparatorBuilder().setSpacing('Small');

    // 6) 하단 2x2 버튼(회색, 활성) — 섹션 4개로 분리(섹션당 버튼 1개)
    const noticeBtn = new ButtonBuilder()
      .setCustomId('notice')
      .setEmoji({ name: 'emoji_5', id: '1424003478275231916' }) // <:emoji_5:1424003478275231916>
      .setLabel('공지사항')
      .setStyle(ButtonStyle.Secondary); // 회색

    const chargeBtn = new ButtonBuilder()
      .setCustomId('charge')
      .setEmoji({ name: 'charge', id: '1424003480007475281' }) // <:charge:1424003480007475281>
      .setLabel('충전')
      .setStyle(ButtonStyle.Secondary);

    const infoBtn = new ButtonBuilder()
      .setCustomId('info')
      .setEmoji({ name: 'info', id: '1424003482247237908' }) // <:info:1424003482247237908>
      .setLabel('내 정보')
      .setStyle(ButtonStyle.Secondary);

    const buyBtn = new ButtonBuilder()
      .setCustomId('buy')
      .setEmoji({ name: 'category', id: '1424003481240469615' }) // <:category:1424003481240469615>
      .setLabel('구매')
      .setStyle(ButtonStyle.Secondary);

    // 섹션 4개로 나눔(섹션 하나당 버튼 하나 → 검증 에러 방지)
    const sectionBtnNotice = new SectionBuilder().setButtonAccessory(noticeBtn);
    const sectionBtnCharge = new SectionBuilder().setButtonAccessory(chargeBtn);
    const sectionBtnInfo   = new SectionBuilder().setButtonAccessory(infoBtn);
    const sectionBtnBuy    = new SectionBuilder().setButtonAccessory(buyBtn);

    // 7) 하단 긴 막대기
    const sepBottom = new SeparatorBuilder().setSpacing('Small');

    // 8) 푸터 섹션
    const footerText = new TextDisplayBuilder().setContent(
      '자동화 로벅스 / 2025 / GMT+09:00'
    );
    const sectionFooter = new SectionBuilder().addTextDisplayComponents(footerText);

    // 컨테이너 조립(섹션/구분선만 넣음)
    const container = new ContainerBuilder()
      .addSectionComponents(sectionTop)
      .addSeparatorComponents(sepTop)
      .addSectionComponents(sectionStock)
      .addSectionComponents(sectionSales)
      .addSeparatorComponents(sepMid)
      // 2x2: 위 두 개 → 아래 두 개 (렌더러가 세로로 쌓아주고, UI는 2x2처럼 보이도록 구성된 빌드 기준)
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

  // 하단 2x2 버튼은 눌러도 화면 반응 배너 안 뜨게 묵음 처리
  if (interaction.isButton()) {
    try {
      await interaction.deferUpdate();
    } catch (_) {}
    return;
  }
});

client.login(process.env.DISCORD_TOKEN);
