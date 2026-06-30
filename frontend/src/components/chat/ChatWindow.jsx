// import React from "react";
// import { Bubble } from "@ant-design/x";
// import { Avatar, Empty } from "antd";
// import { UserOutlined, RobotOutlined } from "@ant-design/icons";

// const rolesConfig = {
//   user: {
//     placement: "end",
//     avatar: <Avatar icon={<UserOutlined />} style={{ background: "#6083b4ff" }} />,
//   },
//   assistant: {
//     placement: "start",
//     avatar: <Avatar icon={<RobotOutlined />} style={{ background: "#83b06dff" }} />,
//   },
// };

// /**
//  * ChatWindow renders the scrollable list of chat bubbles.
//  *
//  * Expected `messages` shape:
//  * [{ key: string, role: "user" | "assistant", content: string, loading?: boolean }]
//  */
// export default function ChatWindow({ messages }) {
//   if (!messages || messages.length === 0) {
//     return (
//       <div
//         style={{
//           height: "100%",
//           display: "flex",
//           alignItems: "center",
//           justifyContent: "center",
//         }}
//       >
//         <Empty
//           image={Empty.PRESENTED_IMAGE_SIMPLE} 
//           description="Say hello to start the conversation" 
//         />
//       </div>
//     );
//   }

//   return (
//     <Bubble.List
//       style={{ height: "100%" }}
//       role={rolesConfig}
//       items={messages.map((message) => ({
//         key: message.key,
//         role: message.role,
//         content: message.content,
//         loading: message.loading,
//       }))}
//     />
//   );
// }



import React from "react";
import { Bubble, Prompts } from "@ant-design/x";
import { Avatar, Empty, Flex, Typography } from "antd";
import {
  UserOutlined,
  RobotOutlined,
  HeartOutlined,
  SmileOutlined,
  CommentOutlined,
  PaperClipOutlined,
} from "@ant-design/icons";

const {Title} = Typography;

const rolesConfig = {
  user: {
    placement: "end",
    avatar: <Avatar icon={<UserOutlined />} style={{ background: "#a6c7f5ff" }} />,
  },
  assistant: {
    placement: "start",
    avatar: <Avatar icon={<RobotOutlined />} style={{ background: "#b1dd9aff" }} />,
  },
};

const HOT_TOPICS = {
  key: "1",
  label: "Hot Topics",
  children: [
    {
      key: "1-1",
      description: "What documents can I ask about?",
      icon: <span style={{ color: "#f93a4a", fontWeight: 700 }}>1</span>,
    },
    {
      key: "1-2",
      description: "Summarize my most recent upload",
      icon: <span style={{ color: "#ff6565", fontWeight: 700 }}>2</span>,
    },
    {
      key: "1-3",
      description: "What can this assistant help me with?",
      icon: <span style={{ color: "#ff8f1f", fontWeight: 700 }}>3</span>,
    },
  ],
};

const DESIGN_GUIDE = {
  key: "2",
  label: "Tips",
  children: [
    {
      key: "2-1",
      icon: <HeartOutlined />,
      label: "Ask naturally",
      description: "Phrase questions like you would to a person.",
    },
    {
      key: "2-2",
      icon: <SmileOutlined />,
      label: "Be specific",
      description: "The more detail you give, the better the answer.",
    },
    {
      key: "2-3",
      icon: <CommentOutlined />,
      label: "Follow up",
      description: "Keep chatting to refine or dig deeper into a topic.",
    },
    {
      key: "2-4",
      icon: <PaperClipOutlined />,
      label: "Attach files",
      description: "Reference uploaded documents directly in your question.",
    },
  ],
};

/**
 * ChatWindow renders the scrollable list of chat bubbles.
 *
 * Expected `messages` shape:
 * [{ key: string, role: "user" | "assistant", content: string, loading?: boolean }]
 *
 * `onPromptSelect` (optional): called with the prompt text when a user clicks
 * a Hot Topics / Tips card in the empty state.
 */
export default function ChatWindow({ messages, onPromptSelect }) {
  if (!messages || messages.length === 0) {
    return (
      <Flex
        vertical
        gap={16}
        align="center"
        justify="center"
        style={{ height: "100%", padding: 16, boxSizing: "border-box" }}
      >
        <Flex align="center" justify="center" gap={10}>
          <Title level={4} style={{ margin: 0 }}>
            Ask Anything...
          </Title>
        </Flex>
        {/* <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Say hello to start the conversation"
        /> */}
        <Flex gap={16} justify="center" style={{ width: "100%", maxWidth: 840 }}>
          <Prompts
            items={[HOT_TOPICS]}
            styles={{
              list: { height: "100%" },
              item: {
                flex: 1,
                backgroundImage: "linear-gradient(123deg, #e5f4ff 0%, #efe7ff 100%)",
                borderRadius: 12,
                border: "none",
              },
              subItem: { padding: 0, background: "transparent" },
            }}
            onItemClick={(info) => onPromptSelect?.(info.data.description)}
          />
          <Prompts
            items={[DESIGN_GUIDE]}
            styles={{
              item: {
                flex: 1,
                backgroundImage: "linear-gradient(123deg, #e5f4ff 0%, #efe7ff 100%)",
                borderRadius: 12,
                border: "none",
              },
              subItem: { background: "#ffffffa6" },
            }}
            onItemClick={(info) => onPromptSelect?.(info.data.description)}
          />
        </Flex>
      </Flex>
    );
  }

  return (
    <Bubble.List
      style={{ height: "100%" }}
      role={rolesConfig}
      items={messages.map((message) => ({
        key: message.key,
        role: message.role,
        content: message.content,
        loading: message.loading,
      }))}
    />
  );
}