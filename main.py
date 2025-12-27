import net.dv8tion.jda.api.JDABuilder;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import net.dv8tion.jda.api.interactions.commands.build.Commands;
import net.dv8tion.jda.api.interactions.components.buttons.Button;
import net.dv8tion.jda.api.requests.GatewayIntent;

public class DiscordBot extends ListenerAdapter {

    public static void main(String[] args) {
        // 봇 토큰을 입력하세요
        String token = "YOUR_NEW_TOKEN_HERE";

        JDABuilder builder = JDABuilder.createDefault(token);
        builder.enableIntents(GatewayIntent.GUILD_MESSAGES, GatewayIntent.MESSAGE_CONTENT);
        builder.addEventListeners(new DiscordBot());
        
        var jda = builder.build();

        // 슬래시 명령어 등록
        jda.updateCommands().addCommands(
            Commands.slash("쿠키체커기", "로블록스 쿠키 체커기 컴포넌트 전송")
        ).queue();
    }

    @Override
    public void onSlashCommandInteraction(SlashCommandInteractionEvent event) {
        if (event.getName().equals("쿠키체커기")) {
            // 버튼 생성
            Button startButton = Button.secondary("start_checker", "로블록스 쿠키 체커기 시작");

            // 메시지 전송 (텍스트 + 버튼)
            event.reply("**로블록스 쿠키 체커기**")
                 .addActionRow(startButton) // 파이썬의 Container 역할을 하는 ActionRow
                 .queue();
        }
    }
}
