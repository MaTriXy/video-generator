# Script Reference Examples

These scripts define the target quality across different topic categories, registers, and lengths. For non-STEM topics, historical topics, or shorter formats, adapt the register while preserving the escalation structure and emotional arc.

| Script | Topic | Register | Length | Gap it fills |
|---|---|---|---|---|
| 1 — Unity deltaTime | Game dev / mechanism | Technical | Long | Frame-rate bug, precise analogy |
| 2 — C++ Pointers | CS / mechanism | Technical | Long | Memory model, box analogy |
| 3 — Neural Networks | AI / mechanism | Technical | Long | Abstract system made concrete |
| 4 — Unreal Actors | Game dev / structure | Technical | Long | Hierarchy and containers |
| 5 — Periodic Table | GK / history | Narrative | Short | Non-STEM, no diagrams, story arc |
| 6 — Product Design | Psychology / systems | Analytical | Long | Cross-industry, behavioural argument, layered framework |

---

### Script 1 — Game Dev / Mechanism (Unity Time.deltaTime)
Your game has a bug you have never seen. It only shows up on someone else's computer, it never throws an error, and it affects every single object that moves in your scene.
Look at these two cubes. They have the same code and speed value. At 30 FPS, they crawl. At 144, they fly. The speed of your game is tied to how fast your player's computer is. Someone on a gaming PC moves two and a half times faster than someone on a laptop. Same build, completely different experience.
If you have ever written transform dot position plus equals speed in Update, your game has this bug right now.
Unity calls Update once per frame. Not once per second. Once per frame. At 60 FPS, your movement code runs 60 times. At 144, it runs 144 times.
If you add 5 units every frame, at 60 FPS you cover 300 units per second. At 144, you cover 720. You were thinking in seconds, but writing in frames. That mismatch is the entire bug.
That is where Time dot deltaTime comes in. Time dot deltaTime tells you how many seconds the last frame took. At 60 FPS, that number is about 16 milliseconds. At 144, about 7. The faster your machine runs, the smaller that number gets.
Multiply your speed by it, and the math changes. Instead of moving 5 units every frame regardless, you are moving 5 units spread evenly across however many frames fit into one second. More frames means smaller steps. Fewer frames means bigger steps. The distance covered in one second stays the same.
This is not just about movement. This also applies to rotation, cooldown timers, color fades. Anything in Update that changes over time without deltaTime is frame-rate dependent. The rule is simple. If it changes over time in Update, multiply by Time dot deltaTime.
One multiplication. That is the difference between a game that works on your machine and a game that works on every machine.

---

### Script 2 — CS / Mechanism (C++ Pointers)
You do not understand C++ until you understand pointers. Not because they are hard. Because everything else in the language sits on top of them.
Every variable you create lives somewhere in memory. Think of it like a row of numbered boxes. Your variable score sits in box 204. The value inside is 10. When you write ampersand score, you are not asking for the value. You are asking for the box number.
A pointer stores a box number instead of a regular value. When you write int star ptr equals ampersand score, you are creating a new box that holds 204 inside it. A box that holds the address of another box. That is all a pointer is.
The star operator follows that address. Star ptr means "go to whatever box number is stored in ptr and give me what is inside." That is called dereferencing.
This is why changing star ptr also changes score. They are not two copies. They are two ways to reach the same box in memory. One by name, one by address.
Here is where it gets useful. Here is a function to double a number. You pass in score, and the function doubles it, but back in main, score has not changed. C plus plus copied the value in. But the function doubled its own local copy and threw it away.
Let's pass a pointer instead. Now the function has the address of the original box. It doubles what is inside, and score in main has changed. You did not copy the data. You told the function where to find it. That is the entire reason pointers exist. Reaching across scopes and modifying data without copying it.
A pointer with no assigned address holds garbage. Some random box number. Dereferencing that means your program just went to a random address and tried to use whatever it found there. That is a crash if you are lucky. If you are unlucky, it corrupts data and you spend hours debugging something that makes no sense. Always initialize your pointers to nullptr if you have nothing to put there yet.
That is what pointers are. Just box numbers pointing to other boxes. Every concept you learn in C++ from here — arrays, references, memory management — will trace back to this one idea.

---

### Script 3 — AI / Mechanism (Neural Networks)
There is no thinking in a neural network. No logic, no reasoning, no understanding. Just one math operation repeated a billion times. And somehow, that is enough.
A neural network starts with numbers. That photo of a dog is not a picture to the machine. It is a grid of pixel values, thousands of them. That pixel grid is the input.
Those numbers get fed into a layer of neurons. Each neuron does one thing. It looks at every input, multiplies each one by a weight — basically how much it cares about that input — adds everything up, and asks one question. Is this signal worth passing on or not? That is all any neuron ever does.
The first layer might detect edges and gradients. The second layer combines those into shapes. An ear, a snout, a paw. The third layer combines shapes into concepts. That combination of ears, snout, and fur is a dog. Each layer builds on the one before it. That stacking of layers is what people mean by deep learning.
That is what a trained network looks like. But it does not start that way. At first, every weight is random. You show it a dog and it says cat. That is where training begins.
The network makes a prediction. You compare it to the correct answer. The gap between them is called the loss. Training is the process of making that loss as small as possible.
You do this through backpropagation. The loss flows backwards through the network and tells each weight how much it contributed to the error. Wrong weights get adjusted. Helpful weights get reinforced. Show it another image and it gives a slightly better answer, you adjust again. Repeat this millions of times and the weights settle into values that detect edges in layer one, shapes in layer two, concepts in layer three. Nobody programmed those features. The weights found them by trying to reduce the loss.
That is what learning means in machine learning. It is not understanding. It is weight adjustment driven by error reduction. The network does not know what a dog is. It has found a weight configuration that produces the right output when dog-like patterns appear at the input.
That language model answering your questions right now was trained this same way. Different architecture, different data, massively different scale. But the same core loop. Input, weights, prediction, loss, adjustment, repeat. That is the entire foundation. Everything else is just scale.

---

### Script 4 — Game Dev / Structure (Unreal Engine Actors)
Delete every component from a character in Unreal and you know what you are left with? An empty Actor. No mesh, no movement, no collision. It cannot do a single thing on its own. And yet that empty Actor is the most important thing in the engine.
An Actor is any object that can exist in a level. It might be a camera, a static mesh, or a player start location. If it is in your level, it is an Actor. In C plus plus, every Actor inherits from one base class called AActor.
But an Actor on its own has no shape, no position, and no behavior. It does not even have a location. What gives it all of that are Components. An Actor is just a container. Components are what you put inside it.
Components come in three layers. At the base, ActorComponent is pure logic — it can tick every frame but has no position in the world. Stack a SceneComponent on top and now you have a transform — location, rotation, scale. This is also where the hierarchy lives. An Actor does not store its own position. It gets it from whichever SceneComponent sits at the root. Add a PrimitiveComponent and now you have something visible — a mesh, a particle system — even physics and collision.
So that gold pickup in your level is not one object. It is an Actor with a hierarchy of Components. A SceneComponent at the root setting the position. A StaticMeshComponent rendering the gold. A ParticleSystemComponent for the sparkle. An AudioComponent for the sound. A BoxComponent for the collision trigger. Five different components, one Actor. Remove any one of them and the Actor still exists. It just loses that one behavior.
Actors get created through spawning and removed by calling Destroy. In between, they can tick every frame, and their Components can tick independently. That is the full lifecycle. Spawn, tick, destroy.
That is what an Actor is. A container. Components decide what it looks like, where it is, and what it does. Every single thing you build in Unreal starts with understanding this relationship.

---

### Script 5 — GK / History (The Periodic Table)
*Note: The hook here opens on a statement the viewer broadly agrees with — this is the one exception in this set, included to show how a historical narrative can open differently from a mechanism-driven script. For new scripts, still apply the hook rules: avoid generic openings the viewer already accepts.*

Gold gets all the glory, but it is just one of one hundred and eighteen elements — and somebody had to organize them all. The first real attempt came from Newlands, who sorted by atomic mass and called it the law of octaves. It sounded elegant, until it fell apart past calcium, cramming unrelated elements together like strangers at a party. Then Mendeleev took over. He wrote every element on a card, kept rearranging them like a high-stakes card game, and eventually fell asleep — only to dream up the answer. He sorted by properties, leaving deliberate gaps for undiscovered elements. Scientists later found them exactly where he predicted. Moseley then switched the sorting from atomic mass to atomic number, and that is the table still on every classroom wall today. One hundred and eighteen elements in. Element one hundred and nineteen? The hunt is on.

---

### Script 6 — Product Design / Psychology (Why Products Lose You)
*Note: Games are used as illustrations but the argument is about product structure, not game development. Use this register for any topic where the insight applies across industries.*

There is a product you paid for and abandoned within a week. There is also a free product you have used almost every day for years without thinking about it. The difference between them is not quality, features, or price. It is the order in which they were built.

Every product that keeps people coming back is assembled in the same sequence: onboarding first, core experience second, progression third, monetization last. Reverse any two of those layers and the whole structure fails — not eventually, immediately.

Onboarding has one job: get the user to the value before they have a reason to leave. Not through a tutorial or a walkthrough, through the experience itself. Flappy Bird had one instruction — a picture of a bird and the word tap. Within two seconds you understood gravity, timing, and failure. No menus, no loading screens, no three-minute introduction to lore you did not ask for. Compare that to any app that opens with an unskippable animation, drops you into eight screens you cannot read, and hands you rewards for actions you have not taken. The user never reaches the value. They leave.

Core experience is where most teams think they start. They do not. They start with the revenue model and reverse-engineer the experience around it. Core experience is about feel, not features. Celeste has three inputs: jump, dash, climb. The developers built in hidden forgiveness — a few extra frames where you can still jump after walking off a ledge, a buffer that catches your input slightly early. You never see those mechanics. You just feel like the product respects you. Candy Crush at higher levels does the opposite. You read the board correctly, make the right moves, and a random number generator hands you an unwinnable state so you spend on extra turns. Most users feel the difference even when they cannot name it.

Progression answers one question: why would this person come back tomorrow? Good progression makes users feel the weight of their choices — invest time in one direction and the experience responds to that investment. Destiny 2 missed this for years, raising the level cap each season and asking players to re-earn what they already had. The number went up. The experience did not change. Players called it a hamster wheel, and they were right.

Monetization comes last because it only works on top of the other three. Genshin Impact's gacha system has brutal base odds, but a pity mechanic guarantees a top-tier reward after enough pulls. Players plan months ahead and build calculators to predict outcomes. It is designed to make money, but it gives users something to strategize around. Diablo Immortal had no such structure — maxing a character was estimated at over a hundred thousand dollars, with a progression system so opaque that even paying players could not see the ceiling. The community walked in the first week.

You can redesign monetization at any point. But if you hollow out the core experience or gut the onboarding to make room for a purchase screen, the whole structure comes down. Most products do not fail because they ran out of ideas. They fail because they started building from the wrong end.
