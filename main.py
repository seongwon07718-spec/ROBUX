const {
    SlashCommandBuilder,
    EmbedBuilder,
    TextDisplayBuilder,
    MessageFlags,
    SeparatorBuilder,
    SeparatorSpacingSize,
    SectionBuilder,
    ThumbnailBuilder,
    ButtonBuilder,
    ButtonStyle,
    MediaGalleryBuilder,
    ContainerBuilder,
    AttachmentBuilder,
    FileBuilder
} = require('discord.js');
const path = require('path');
const fs = require('fs');


module.exports = {
    data: new SlashCommandBuilder()
        .setName('new-update')
        .setDescription('This is components version 2.'),
    async execute(interaction, client) {
        // Command execution logic goes here

        const container = new ContainerBuilder();

        const media = new MediaGalleryBuilder()
            .addItems([
                {
                    media: {
                        url: 'https://i.ibb.co/yFsBTGDL/docs-header.jpg'
                    }
                }
            ])
        
        container.addMediaGalleryComponents(media);

        const textTop = new TextDisplayBuilder()
            .setContent(`## Introducing New Components for Messages!\nWe're bringing new components to messages that you can use in your apps. They allow you to have full control over the layout of your messages.\n\nOur previous components system. while functional, had limitations:\n- Content, attachments, embed, buttons, and components had to follow fixed positioning rules\n- Visual styling options were limited\n\nOur new component system addresses these challenged with fully composible components that can be arragned and laid out in any order, allowing for a more flexible and visually appealing design. Check out the [changelog](https://i.ibb.co/yFsBTGDL/docs-header.jpg) for more details.`);

        container.addTextDisplayComponents(textTop);

        const media2 = new MediaGalleryBuilder()
            .addItems([
                {
                    media: {
                        url: 'https://i.ibb.co/RTSs4JWp/components-hero.png'
                    }
                }
            ])

        container.addMediaGalleryComponents(media2);

        const text1 = new TextDisplayBuilder().setContent('A breif overview of components');
        const button1 = new ButtonBuilder().setLabel('Overview').setURL('https://youtube.com').setStyle(ButtonStyle.Link);

        const section1 = new SectionBuilder()
            .addTextDisplayComponents(text1)
            .setButtonAccessory(button1);

        container.addSectionComponents(section1);

        const text2 = new TextDisplayBuilder().setContent('A breif overview of components');
        const button2 = new ButtonBuilder().setLabel('Overview').setURL('https://youtube.com').setStyle(ButtonStyle.Link);

        const section2 = new SectionBuilder()
            .addTextDisplayComponents(text2)
            .setButtonAccessory(button2);

        container.addSectionComponents(section2);

        const text3 = new TextDisplayBuilder().setContent('A breif overview of components');
        const button3 = new ButtonBuilder().setLabel('Overview').setURL('https://youtube.com').setStyle(ButtonStyle.Link);

        const section3 = new SectionBuilder()
            .addTextDisplayComponents(text3)
            .setButtonAccessory(button3);

        container.addSectionComponents(section3);


        const separator = new SeparatorBuilder();

        container.addSeparatorComponents(separator);

        const text4 = new TextDisplayBuilder().setContent(`-# This message was composed using components, check out the request:`)

        container.addTextDisplayComponents(text4);

        const filePath = path.join(__dirname, '../../../message-data.json');
        const fileContent = await fs.promises.readFile(filePath, 'utf8');

        const attachment = new AttachmentBuilder(Buffer.from(fileContent), {
            name: 'message.json'
        })

        const file = new FileBuilder().setURL('attachment://message.json');

        container.addFileComponents(file);

        interaction.reply({
            flags: MessageFlags.IsComponentsV2,
            components: [container],
            files: [attachment]
        })





    }
};
