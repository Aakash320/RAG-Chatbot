import React, { useEffect, useState } from "react";
import { ThoughtChain } from "@ant-design/x";
import { Collapse, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

const STEP_TITLES = {
  detect_intent: "Detecting intent",
  rewrite_query: "Rewriting query",
  retrieve: "Retrieving context",
  generate: "Generating answer",
};

const STATUS_ICON = {
  pending: <LoadingOutlined />,
  success: <CheckCircleOutlined />,
  error: <CloseCircleOutlined />,
};

/**
 * Turns the raw statusSteps events collected from the SSE stream (one
 * "start" + one "end" event per pipeline node) into a single ThoughtChain
 * item per node — it starts "pending" and resolves to "success" once the
 * matching "end" event arrives.
 */
function buildThoughtChainItems(statusSteps, hasFailed) {
  const order = [];
  const byStep = {};

  for (const event of statusSteps || []) {
    if (!byStep[event.step]) {
      byStep[event.step] = { status: "pending", description: event.message, detail: null };
      order.push(event.step);
    }
    if (event.phase === "end") {
      byStep[event.step].status = "success";
      byStep[event.step].description = event.message;
      byStep[event.step].detail = event.detail || null;
    }
  }

  return order.map((step) => {
    const s = byStep[step];
    const status = hasFailed && s.status === "pending" ? "error" : s.status;
    return {
      key: step,
      title: STEP_TITLES[step] || step,
      status,
      icon: STATUS_ICON[status],
      description: <StepDetail step={step} description={s.description} detail={s.detail} />,
    };
  });
}

function StepDetail({ step, description, detail }) {
  return (
    <div style={{ fontSize: 12 }}>
      <div>{description}</div>

      {step === "rewrite_query" && detail?.rewritten_query && (
        <Text type="secondary" style={{ display: "block", marginTop: 4 }}>
          → "{detail.rewritten_query}"
        </Text>
      )}

      {step === "retrieve" && detail?.chunks?.length > 0 && (
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
          {detail.chunks.map((c, idx) => (
            <div key={idx} style={{ display: "flex", gap: 6, alignItems: "baseline" }}>
              <Tag style={{ margin: 0 }}>
                {c.source_file} · {Math.round(c.score * 100)}%
              </Tag>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {c.text}
              </Text>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Renders the reasoning steps for a single assistant message, collected
 * in `message.statusSteps` while the SSE response streams in.
 *
 * Auto-expands while the message is still in progress, and auto-collapses
 * once `isComplete` becomes true — the user can still toggle it manually
 * afterward.
 */
export default function MessageThoughtChain({ statusSteps, hasFailed, isComplete }) {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (isComplete) setOpen(false);
  }, [isComplete]);

  if (!statusSteps || statusSteps.length === 0) return null;

  const items = buildThoughtChainItems(statusSteps, hasFailed);

  return (
    <Collapse
      size="small"
      ghost
      activeKey={open ? ["thoughts"] : []}
      onChange={(keys) => setOpen(keys.length > 0)}
      style={{ marginBottom: 8 }}
      items={[
        {
          key: "thoughts",
          label: (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {isComplete ? `Thought process · ${items.length} step(s)` : "Thinking..."}
            </Text>
          ),
          children: <ThoughtChain items={items} />,
        },
      ]}
    />
  );
}