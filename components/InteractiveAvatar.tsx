import type { StartAvatarResponse } from "@heygen/streaming-avatar";

import StreamingAvatar, {
  AvatarQuality,
  StreamingEvents, TaskMode, TaskType, VoiceEmotion,
} from "@heygen/streaming-avatar";
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  Divider,
  Input,
  Select,
  SelectItem,
  Spinner,
  Chip,
  Tabs,
  Tab,
} from "@nextui-org/react";
import { useEffect, useRef, useState } from "react";
import { useMemoizedFn, usePrevious } from "ahooks";

import InteractiveAvatarTextInput from "./InteractiveAvatarTextInput";

import {AVATARS, STT_LANGUAGE_LIST} from "@/app/lib/constants";

export default function InteractiveAvatar() {
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isLoadingRepeat, setIsLoadingRepeat] = useState(false);
  const [stream, setStream] = useState<MediaStream>();
  const [debug, setDebug] = useState<string>();
  const [knowledgeId, setKnowledgeId] = useState<string>("");
  const [avatarId, setAvatarId] = useState<string>("");
  const [language, setLanguage] = useState<string>('en');
  const [isRecording, setIsRecording] = useState(false);

  const [data, setData] = useState<StartAvatarResponse>();
  const [text, setText] = useState<string>("");
  const mediaStream = useRef<HTMLVideoElement>(null);
  const avatar = useRef<StreamingAvatar | null>(null);
  const [chatMode, setChatMode] = useState("text_mode");
  const [isUserTalking, setIsUserTalking] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  async function fetchAccessToken() {
    try {
      const response = await fetch("/api/get-access-token", {
        method: "POST",
      });
      const token = await response.text();

      console.log("Access Token:", token); // Log the token to verify

      return token;
    } catch (error) {
      console.error("Error fetching access token:", error);
    }

    return "";
  }

  async function processRecordedAudio(audioBlob: Blob) {
    const reader = new FileReader();
    reader.readAsDataURL(audioBlob);
    reader.onloadend = async () => {
      const base64Audio = reader.result;
  
      console.log("📤 Sending recorded audio to backend...");
  
      const response = await fetch("/api/audio-to-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: base64Audio }),
      });
  
      const data = await response.json();
  
      if (response.ok) {
        console.log("🎤 Transcription received:", data.transcript);
  
        if (!data.transcript.trim()) {
          console.log("🚫 Ignoring empty transcript.");
          return; // Ignore if no speech was detected
        }
  
        setDebug(`User said: ${data.transcript}`);
  
        // ✅ Ensure `handleSpeak()` is called AFTER `text` updates
        setText(data.transcript);
        setTimeout(() => {
          handleSpeak(data.transcript);
        }, 100); // Add slight delay to ensure React state updates
      } else {
        console.error("❌ Error processing audio:", data.error);
        setDebug("Error processing audio");
      }
    };
  }
  
  
  function handleVoiceRecording() {
    if (!isRecording) {
      // Start recording
      navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];
  
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };
  
        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
  
          // ✅ Process the recorded audio
          processRecordedAudio(audioBlob);
        };
  
        mediaRecorder.start();
        setIsRecording(true);
        console.log("🎤 Recording started...");
      }).catch((err) => console.error("Error accessing microphone:", err));
    } else {
      // Stop recording
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        setIsRecording(false);
        console.log("🛑 Recording stopped.");
      }
    }
  }
  

  async function startSession() {
    setIsLoadingSession(true);
    const newToken = await fetchAccessToken();

    avatar.current = new StreamingAvatar({
      token: newToken,
    });
    avatar.current.on(StreamingEvents.AVATAR_START_TALKING, (e) => {
      console.log("Avatar started talking", e);
    });
    avatar.current.on(StreamingEvents.AVATAR_STOP_TALKING, (e) => {
      console.log("Avatar stopped talking", e);
    });
    avatar.current.on(StreamingEvents.STREAM_DISCONNECTED, () => {
      console.log("Stream disconnected");
      endSession();
    });
    avatar.current?.on(StreamingEvents.STREAM_READY, (event) => {
      console.log(">>>>> Stream ready:", event.detail);
      setStream(event.detail);
    });
    
    try {
      const res = await avatar.current.createStartAvatar({
        quality: AvatarQuality.High,
        avatarName: "Wayne_20240711",
        knowledgeId: knowledgeId, // Or use a custom `knowledgeBase`.
        voice: {
          rate: 1, // 0.5 ~ 1.5
          emotion: VoiceEmotion.EXCITED,
          // elevenlabsSettings: {
          //   stability: 1,
          //   similarity_boost: 1,
          //   style: 1,
          //   use_speaker_boost: false,
          // },
        },
        language: language,
        disableIdleTimeout: true,
      });

      setData(res);
      // default to voice mode
      setChatMode("voice_mode");
    } catch (error) {
      console.error("Error starting avatar session:", error);
    } finally {
      setIsLoadingSession(false);
    }
  }
    

  async function handleSpeak(message?: string) {
    const inputText = message || text; // ✅ Use the latest transcript
  
    if (!inputText.trim()) {
      console.log("🚫 Ignoring empty input.");
      return; // Ignore if no actual user input
    }
  
    setIsLoadingRepeat(true);
  
    try {
      console.log("📤 Sending text to OpenAI:", inputText);
  
      const response = await fetch("/api/chatgpt", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: inputText }), // ✅ Use the latest transcript
      });
  
      const data = await response.json();
  
      if (response.ok) {
        const reply = data.reply;
        console.log("🗣 Bot's Response:", reply);
  
        await avatar.current?.speak({
          text: reply,
          taskType: TaskType.REPEAT,
          taskMode: TaskMode.SYNC,
        });
  
        setDebug(`Avatar said: ${reply}`);
      } else {
        setDebug(data.error || "Failed to get response from OpenAI");
      }
    } catch (error) {
      console.error("❌ Error fetching OpenAI response:", error);
      setDebug("Error fetching OpenAI response");
    } finally {
      setIsLoadingRepeat(false);
    }
  }
  
  

  async function handleInterrupt() {
    if (!avatar.current) {
      setDebug("Avatar API not initialized");

      return;
    }
    await avatar.current
      .interrupt()
      .catch((e) => {
        setDebug(e.message);
      });
  }
  async function endSession() {
    await avatar.current?.stopAvatar();
    setStream(undefined);
  }

  const handleChangeChatMode = useMemoizedFn(async (v) => {
    if (v === chatMode) {
      return;
    }
    if (v === "text_mode") {

    }
    setChatMode(v);
  });

  useEffect(() => {
    return () => {
      endSession();
    };
  }, []);

  useEffect(() => {
    if (stream && mediaStream.current) {
      mediaStream.current.srcObject = stream;
      mediaStream.current.onloadedmetadata = () => {
        mediaStream.current!.play();
        setDebug("Playing");
      };
    }
  }, [mediaStream, stream]);

  return (
    <div className="w-full flex flex-col gap-4">
      <Card>
        <CardBody className="h-[500px] flex flex-col justify-center items-center">
          {stream ? (
            <div className="h-[500px] w-[900px] justify-center items-center flex rounded-lg overflow-hidden">
              <video
                ref={mediaStream}
                autoPlay
                playsInline
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "contain",
                }}
              >
                <track kind="captions" />
              </video>
              <div className="flex flex-col gap-2 absolute bottom-3 right-3">
                <Button
                  className="bg-gradient-to-tr from-indigo-500 to-indigo-300 text-white rounded-lg"
                  size="md"
                  variant="shadow"
                  onClick={handleInterrupt}
                >
                  Interrupt task
                </Button>
                <Button
                  className="bg-gradient-to-tr from-indigo-500 to-indigo-300  text-white rounded-lg"
                  size="md"
                  variant="shadow"
                  onClick={endSession}
                >
                  End session
                </Button>
              </div>
            </div>
          ) : !isLoadingSession ? (
            <div className="h-full justify-center items-center flex flex-col gap-8 w-[500px] self-center">
              <div className="flex flex-col gap-2 w-full">
                <Select
                  label="Select language"
                  placeholder="Select language"
                  className="max-w-xs"
                  selectedKeys={[language]}
                  onChange={(e) => {
                    setLanguage(e.target.value);
                  }}
                >
                  {STT_LANGUAGE_LIST.map((lang) => (
                    <SelectItem key={lang.key}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </Select>
              </div>
              <Button
                className="bg-gradient-to-tr from-indigo-500 to-indigo-300 w-full text-white"
                size="md"
                variant="shadow"
                onClick={startSession}
              >
                Start session
              </Button>
            </div>
          ) : (
            <Spinner color="default" size="lg" />
          )}
        </CardBody>
        <Divider />
        <CardFooter className="flex flex-col gap-3 relative">
          <Tabs
            aria-label="Options"
            selectedKey={chatMode}
            onSelectionChange={(v) => {
              handleChangeChatMode(v);
            }}
          >
            <Tab key="text_mode" title="Text mode" />
            <Tab key="voice_mode" title="Voice mode" />
          </Tabs>
          {chatMode === "text_mode" ? (
            <div className="w-full flex relative">
              <InteractiveAvatarTextInput
                disabled={!stream}
                input={text}
                label="Chat"
                loading={isLoadingRepeat}
                placeholder="Type something for the avatar to respond"
                setInput={setText}
                onSubmit={handleSpeak}
              />
              {text && (
                <Chip className="absolute right-16 top-3">Listening</Chip>
              )}
            </div>
          ) : (
            <div className="w-full text-center">
                <Button
                  className={`bg-gradient-to-tr ${
                    isRecording ? "from-red-500 to-red-300" : "from-indigo-500 to-indigo-300"
                  } text-white rounded-lg`}
                  size="md"
                  variant="shadow"
                  onClick={handleVoiceRecording}
                >
                  {isRecording ? "Stop Recording" : "Start Recording"}
                </Button>

            </div>
          )}
        </CardFooter>
      </Card>
      <p className="font-mono text-right">
        <span className="font-bold">Console:</span>
        <br />
        {debug}
      </p>
    </div>
  );
}
