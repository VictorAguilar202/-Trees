const decisionCard = document.querySelector("#decision-card");
const pathPanel = document.querySelector("#path-panel");
const pathList = document.querySelector("#path-list");
const stepLabel = document.querySelector("#step-label");
const treeMap = document.querySelector("#tree-map");

let currentNode = null;
let path = [];

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "The request could not be completed.");
  }
  return data;
}

function renderTree(node, compact = false) {
  const wrapper = document.createElement("div");
  const box = document.createElement("div");
  box.className = `tree-node${node.recommendation ? " tree-node--leaf" : ""}${compact ? " tree-node--compact" : ""}`;
  box.textContent = node.title;
  wrapper.append(box);

  if (!node.recommendation) {
    const children = document.createElement("div");
    children.className = "tree-children";
    for (const answer of ["yes", "no"]) {
      const branch = document.createElement("div");
      branch.className = "tree-branch";
      const label = document.createElement("span");
      label.className = "tree-branch-label";
      label.textContent = answer.toUpperCase();
      branch.append(label, renderTree(node[answer], true));
      children.append(branch);
    }
    wrapper.append(children);
  }
  return wrapper;
}

function renderPath() {
  pathList.replaceChildren();
  for (const step of path) {
    const item = document.createElement("li");
    item.textContent = step.answer ? `${step.label} · ${step.answer}` : step.label;
    if (step.answer) {
      item.classList.add("path-answer");
    }
    pathList.append(item);
  }
  pathPanel.hidden = path.length === 0;
}

function showQuestion(node) {
  currentNode = node;
  stepLabel.textContent = `QUESTION ${path.filter((item) => item.answer).length + 1}`;
  decisionCard.replaceChildren();

  const compass = document.createElement("div");
  compass.className = "compass";
  compass.setAttribute("aria-hidden", "true");
  compass.textContent = "N";
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = node.title.toUpperCase();
  const title = document.createElement("h2");
  title.textContent = node.prompt;
  const description = document.createElement("p");
  description.className = "decision-description";
  description.textContent = "Choose the answer that best matches your observation.";
  const answers = document.createElement("div");
  answers.className = "answers";

  for (const [answer, label, secondary] of [
    ["yes", "Yes", false],
    ["no", "No", true],
  ]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `answer-button${secondary ? " answer-button--secondary" : ""}`;
    button.textContent = label;
    button.addEventListener("click", () => chooseAnswer(answer));
    answers.append(button);
  }
  decisionCard.append(compass, eyebrow, title, description, answers);
  renderPath();
}

function showOutcome(node) {
  currentNode = null;
  stepLabel.textContent = "OUTCOME";
  path.push({ label: node.title });
  decisionCard.replaceChildren();

  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = "SUGGESTED NEXT STEP";
  const title = document.createElement("h2");
  title.textContent = node.title;
  const recommendation = document.createElement("div");
  recommendation.className = "recommendation";
  const recommendationLabel = document.createElement("strong");
  recommendationLabel.textContent = "Recommendation";
  recommendation.append(recommendationLabel, document.createTextNode(node.recommendation));
  const rationale = document.createElement("p");
  rationale.className = "decision-description";
  rationale.textContent = node.rationale;
  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "primary-button";
  reset.textContent = "Review another observation";
  reset.addEventListener("click", startAssessment);
  decisionCard.append(eyebrow, title, recommendation, rationale, reset);
  renderPath();
}

async function chooseAnswer(answer) {
  if (!currentNode) return;
  const node = currentNode;
  path.push({ label: node.title, answer: answer.toUpperCase() });
  try {
    const nextNode = await requestJson("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node_id: node.id, answer }),
    });
    if (nextNode.recommendation) {
      showOutcome(nextNode);
    } else {
      showQuestion(nextNode);
    }
  } catch (error) {
    currentNode = node;
    path.pop();
    renderPath();
    showError(error);
  }
}

function showError(error) {
  const message = document.createElement("p");
  message.className = "recommendation";
  message.setAttribute("role", "alert");
  message.textContent = error.message;
  decisionCard.append(message);
}

async function startAssessment() {
  path = [];
  pathPanel.hidden = true;
  try {
    showQuestion(await requestJson("/api/tree"));
  } catch (error) {
    showError(error);
  }
}

document.querySelector("#start-button").addEventListener("click", startAssessment);
document.querySelector("#reset-button").addEventListener("click", startAssessment);

requestJson("/api/tree")
  .then((tree) => treeMap.replaceChildren(renderTree(tree)))
  .catch((error) => {
    treeMap.replaceChildren();
    const message = document.createElement("p");
    message.className = "loading";
    message.setAttribute("role", "alert");
    message.textContent = `The decision tree could not be loaded: ${error.message}`;
    treeMap.append(message);
  });
