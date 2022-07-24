package main

import (
	"errors"
	"io"
	"log"
	"mime"
	"net/url"
	"os"
	"os/exec"
	"path"
	"regexp"
	"strings"
	"time"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api"
	yt "github.com/kkdai/youtube/v2"
)

type audio struct {
	title string
	path  string
}

const TOKEN = "YOUTUBE_TELEGRAM_BOT_TOKEN"

func GetBot() *tgbotapi.BotAPI {
	token, ok := os.LookupEnv(TOKEN)
	if !ok {
		log.Panicf("set telegram bot token via env variable '%s'", TOKEN)
	}
	bot, err := tgbotapi.NewBotAPI(token)
	if err != nil {
		log.Panic(err)
	}
	log.Printf("set up bot with: %s token", token)
	bot.Debug = true
	return bot
}

func main() {
	log.Println("starting up...")
	re, _ := regexp.Compile(`^\/(d)\s+(https:\/\/(?:(?:youtu\.be)|(?:(?:www.)?youtube.com/watch)).*)$`)

	bot := GetBot()
	update := tgbotapi.NewUpdate(0)
	update.Timeout = 60
	updates, err := bot.GetUpdatesChan(update)
	if err != nil {
		log.Panic(err)
	}

	for update := range updates {
		var msg *tgbotapi.Message

		if update.Message != nil {
			msg = update.Message
		} else if update.ChannelPost != nil {
			msg = update.ChannelPost
		} else {
			log.Printf("Skipping update...")
			continue
		}
		log.Printf("[%d] %s", msg.Chat.ID, msg.Text)
		match := re.FindAllStringSubmatch(msg.Text, -1)
		if len(match) != 1 || match[0][1] != "d" {
			reply := tgbotapi.NewMessage(msg.Chat.ID, "Usage: /d <youtube video url>")
			reply.ReplyToMessageID = msg.MessageID
			message, err := bot.Send(reply)
			if err != nil {
				log.Printf("Failed to answer: %s", err)
				continue
			}
			time.AfterFunc(30*time.Second, func() {
				message := tgbotapi.NewDeleteMessage(message.Chat.ID, message.MessageID)
				bot.DeleteMessage(message)
			})
			continue
		}
		url := match[0][2]
		go download_video(url, msg, bot)
	}
}

func download_video(url string, msg *tgbotapi.Message, bot *tgbotapi.BotAPI) {
	log.Printf("Start downloading %s", url)
	download_msg := tgbotapi.NewMessage(msg.Chat.ID, "Start download")
	sent_download_msg, _ := bot.Send(download_msg)
	song, err := Download(url)
	if err != nil {
		log.Printf("error: %e", err)
		bot.Send(tgbotapi.NewMessage(msg.Chat.ID, err.Error()))
		return
	}
	log.Printf("Start uploading song to telegram chat: %s", *song)
	song_msg := tgbotapi.NewAudioUpload(msg.Chat.ID, *song)
	song_msg.ReplyToMessageID = msg.MessageID
	bot.Send(song_msg)
	defer os.Remove(*song)
	go bot.DeleteMessage(tgbotapi.NewDeleteMessage(sent_download_msg.Chat.ID, sent_download_msg.MessageID))
	go bot.DeleteMessage(tgbotapi.NewDeleteMessage(msg.Chat.ID, msg.MessageID))
}

func Download(video_url string) (*string, error) {
	client := yt.Client{}
	video_id, err := getVideoID(video_url)
	if err != nil {
		return nil, err
	}
	video, err := client.GetVideo(video_id)
	if err != nil {
		return nil, err
	}
	formats := video.Formats.WithAudioChannels()
	formats.Sort()
	format := &formats[0]
	stream, _, err := client.GetStream(video, format)
	if err != nil {
		return nil, err
	}

	mime_ := strings.SplitN(format.MimeType, ";", 1)[0]
	exts, _ := mime.ExtensionsByType(mime_)
	fpath := path.Join("/tmp/", normalize_name(video.Title)+exts[0])
	log.Printf("Downloading file: %s", fpath)
	file, err := os.Create(fpath)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	defer os.Remove(file.Name())
	defer stream.Close()
	// Write the body to file
	_, err = io.Copy(file, stream)
	if err != nil {
		return nil, err
	}
	log.Printf("Download success: %s", fpath)

	song, err := convert(video, file)

	if err != nil {
		return nil, err
	}
	return &song, nil
}
func normalize_name(value string) string {
	return strings.Trim(regexp.MustCompile(`([\W]+)`).ReplaceAllString(value, "_"), "_")
}

func convert(video *yt.Video, file *os.File) (string, error) {
	ffmpeg_path, err := exec.LookPath("ffmpeg")
	if err != nil {
		return "", err
	}
	ext := path.Ext(file.Name())
	mp3_file_path := strings.Replace(file.Name(), ext, "", 1)
	mp3_file_path = strings.Replace(mp3_file_path, path.Base(mp3_file_path), video.Title, 1)
	mp3_file_path = regexp.MustCompile(`([ ()])`).ReplaceAllString(mp3_file_path, `\$1`)
	mp3_file_path += ".mp3"
	log.Printf("start converting audio to: %s", mp3_file_path)
	err = exec.Command(ffmpeg_path, "-i", file.Name(), mp3_file_path, "-y").Run()
	if err != nil {
		return "", err
	}
	log.Printf("successfully converted audio for %s", mp3_file_path)
	return mp3_file_path, nil
}

func getVideoID(video_url string) (string, error) {
	u, err := url.Parse(video_url)
	if err != nil {
		log.Printf("failed to extract video id")
		return "", err
	}
	hostname := u.Hostname()
	if hostname == "youtu.be" {
		return strings.SplitN(strings.Trim(u.Path, "/"), "/", 1)[0], nil
	} else if strings.HasSuffix(hostname, "youtube.com") {
		return u.Query().Get("v"), nil
	}
	return "", errors.New("unsupported hostname")
}
