"""Optional text-only refresh of stock discoveries; custom Library content wins."""
TEXT_BASE = 0x338000
STRIDE = 256
DESCRIPTIONS = (
    'These stone rings frame the midsummer sunrise and midwinter sunset. Prehistoric builders moved enormous stones to raise them. A sacred gathering place, a calendar, or both? Their purpose still invites wonder.',
    'A decree cut into granodiorite bears three scripts: hieroglyphs, Demotic and Greek. Two languages tell the same story. Could comparing these lines unlock the long-silent voices of ancient Egypt?',
    "Khufu's immense tomb rises above the desert, its four sides facing the cardinal directions. Countless stone blocks form a mountain made by human hands. Even a king's ambition seldom casts so great a shadow.",
    "An armored back breaks the river's surface, then vanishes without a ripple. This great reptile waits almost unseen at the water's edge. Admire its patient hunting from somewhere well beyond those jaws.",
    "Steep-sided pyramids rise from Nubia's desert sands. Smaller than Egypt's famous monuments, they mark the royal burial grounds of Kush. Here, another kingdom set its memories in stone.",
    'The Blue Nile plunges over a broad rocky ledge, filling the air with spray. Known as the smoking waters, these falls announce themselves long before they come into view. Prepare for a very damp journal.',
    "A swollen trunk and spreading branches give this tree an extraordinary silhouette. Its bark supplies useful fibers, and its fruit is edible. A single baobab can seem like a whole village's storehouse.",
    'Sailors report a vast winged reptile with a long, toothless beak. It skims above the water as though searching for fish. Is it an ancient survivor, or a tale that grew with every telling?',
    'The Zambezi drops into a deep gorge beneath a towering cloud of spray. Its thunder carries across the country. No sailor who sees this wall of falling water is likely to forget it.',
    'A weathered stone pillar records the voyage of Diogo Cao near the Congo. Such markers proclaim how far an expedition has sailed. Finding one here makes the map feel a little less empty.',
    'A towering mound rises over a busy insect colony. Beneath its hard walls lies a network of passages, built grain by grain. These tiny workers have raised a fortress without a single shipwright.',
    'An earthen mosque rises in warm, sculpted tiers. Its walls depend on skilled maintenance, with fresh earth renewing the surface. A place of worship becomes a testament to the hands that care for it.',
    'Bands of armor cover this small, industrious digger. Its nose searches the ground while strong claws turn the soil. It carries protection wherever it goes, yet leaves its tracks as plainly as any traveler.',
    'Around Lake Tele, people tell of a huge creature with a long neck and powerful tail. They call it Moquele Mubembe. The water offers few answers, and every distant ripple seems to promise one.',
    'Moonlight catches the spray and draws a pale rainbow across the darkness. The colors are faint, but the sight is unmistakable. Lucky omen or simple wonder, it gives the night watch something to remember.',
    'Stripes cover the head and forequarters of this zebra, fading toward its brown hindquarters. Seen among its boldly patterned relatives, it seems to wear only half a uniform. Nature has no need of matching coats.',
    "A stone monument recalls the voyage of Bartolomeu Dias around Africa's southern waters. Beyond the inscription lie dangerous seas and uncertain winds. A quiet marker bears witness to a very difficult passage.",
    'Great walls of fitted stone rise without mortar at Zimbabwe. Built by a Shona kingdom, this city flourished through craftsmanship and trade. Its ruined passages speak of wealth far beyond the coast.',
    'A mandrill turns a brilliantly colored face toward the expedition. Its powerful build deserves as much notice as its vivid markings. This forest resident is far better admired than approached.',
    'A heavy, flightless bird walks beneath the island trees, carrying an enormous hooked bill. The dodo seems wonderfully at home here. A creature need not fly to belong to a world of distant shores.',
    "A chameleon grips a branch while its eyes survey different directions. Its changing colors are more than camouflage. Then a sudden flick of its sticky tongue ends an insect's afternoon.",
    "Papyrus grows in dense stands beside the water. Ancient Egyptian scribes fashioned its stems into writing sheets. A handful of reeds could carry a merchant's accounts, a royal command, or a story across centuries.",
    'Dark liquid seeps from the earth and spreads across the water. A flame makes the strange substance burn. Useful fuel or dangerous curiosity, this burning water demands a more cautious experiment than most discoveries.',
    'Brick streets and carefully planned drains cross the ruins of Mohenjo-Daro. This ancient Indus city made room for daily life as well as impressive buildings. Its quiet channels reveal remarkable practical skill.',
    "The king cobra raises its head and spreads a warning hood. This enormous venomous snake commands respect without taking another step. The expedition's wisest discovery may be the distance needed to observe it.",
    'Villages stand above Inle Lake on timber stilts, with cultivated beds floating nearby. Water shapes the roads, homes and harvests. Here, a farmer may need a boat as often as a hoe.',
    "Golden images of the Buddha shine among Ayutthaya's temples. The capital's sacred buildings reveal patient artistry and generous patronage. Even a traveler intent on trade may find reason to linger quietly.",
    'A hornbill passes overhead, its great curved bill giving it an unmistakable profile. Among the branches, bright fruit attracts its attention. Such a remarkable face could scarcely be mistaken for another bird.',
    "Stone towers rise above Angkor Wat's galleries and carved walls. Built for Vishnu and later used for Buddhist worship, the temple gathers centuries of devotion into an astonishing work of Khmer architecture.",
    'Travelers speak of a bird with a human face and a voice of surpassing beauty. They call it Kalavinka. No melody in the forest quite settles the question of whether the singer is real or imagined.',
    "What seems a plant sprouting from a caterpillar is a fungus growing from its host. Collected as a valued traditional remedy, this strange specimen blurs the boundary between an insect's end and another life's beginning.",
    'At Toro, traces of a rice-growing village reveal homes, fields and raised storehouses. Lifting grain above the damp ground helped protect the harvest. Small, practical inventions can sustain an entire community.',
    "Fearsome masked visitors arrive to rebuke laziness and urge good behavior. These are the Namahage, figures in local tradition. Their appearance may frighten a newcomer, but their visit belongs to the community's celebrations.",
    "Stone figures keep watch along the approach to Qian Ling's imperial tombs. The silent procession lends grandeur to the hillside. Even without a living guard, this royal resting place commands a respectful approach.",
    'Walls and watchtowers follow the ridges into the distance. Raised and rebuilt across generations, these defenses join engineering with formidable terrain. From one tower, the next already looks impossibly far away.',
    'A hedgehog noses through the undergrowth, then curls into a prickly ball when disturbed. Its spines turn a small animal into a difficult mouthful. The expedition wisely allows it to uncurl in peace.',
    "Black-and-white fur makes this bamboo-eating bear instantly recognizable. Powerful jaws work through tough stems with patient ease. The panda's quiet meal is no invitation to forget that it is still a bear.",
    'A vast flock darkens the sky, the rush of wings swelling above the trees. Passenger pigeons gather in astonishing numbers. A single bird is handsome; a whole moving cloud of them is something else entirely.',
    'Carved figures rise one above another on a tall wooden pole. Such works can preserve family histories and identities. Their meaning belongs to the people who made them, and deserves more than a hurried guess.',
    'Small pieces of jade form a carefully fitted mask. Its polished surface catches the light with a deep green glow. Whatever ceremony it served, the patient skill of its maker remains plain to see.',
    'The still waters of Guatavita conceal a history of precious offerings. Muisca ceremonies helped inspire tales of El Dorado. Looking into the lake, a traveler can understand how a ritual became a golden dream.',
    'A cactus stands where less hardy plants would wither. Its thick stem stores water, while spines guard its surface. In this dry country, survival has produced a most unusual kind of architecture.',
    'An iguana rests on a branch, its crest giving it the look of a small dragon. Much of its food comes from plants. Disturb it, however, and the powerful tail may prove less peaceful than its meal.',
    "What looks like a toothed mouth is a pair of modified leaves. An insect touches the trigger hairs and the trap closes. The Venus' flytrap has found a remarkable way to supplement what poor soil provides.",
    'A broad river breaks into roaring falls and clouds of spray. At Niagara, moving water seems to fill the whole horizon. Conversation becomes difficult; remembering the sight will be much easier.',
    "Huge floating leaves spread across the Amazon's quiet waters. Raised rims and strong ribs give them remarkable structure. Among the smaller plants, this water lily looks almost like a fleet at anchor.",
    'An anaconda slips through the water with scarcely a sound. This great snake coils around its prey rather than using venom. Along a muddy bank, a heavy trail is quite enough evidence for a cautious observer.',
    "The incoming tide drives a powerful bore upstream, sending a rolling wall of water against the river's flow. Called the pororoca, it turns a familiar channel into a hazard no careless boatman should underestimate.",
    'A matamata rests so still that its rough shell and ragged head resemble fallen leaves. In muddy water, the disguise is excellent. A closer look reveals that this piece of river debris has eyes.',
    'Logs lashed together form a broad sailing raft, with a simple shelter above the deck. The balsa shows how local materials can support coastal trade. A vessel need not resemble a European ship to serve its sailors well.',
    "Sharp teeth make the piranha's reputation easy to understand. Its diet can include fish, insects and even fruit. The river's dangers are real enough without turning every small ripple into a feeding frenzy.",
    'A large, hairy spider waits near its refuge. The tarantula is an imposing hunter, chiefly of smaller creatures. Its patient stillness gives the expedition ample time to decide who will sketch it.',
    'A strange feathered creature is described with teeth, clawed wings and a long bony tail. The report seems to join bird and reptile in one body. If true, it would give every naturalist aboard something to argue about.',
    'A tiny golden frog gleams among the leaves. Such bright beauty invites a closer look, but its poisonous skin calls for restraint. Some treasures are best brought home as careful drawings.',
    'A toucan balances among the branches, carrying a bill that seems far too large for its owner. Fruit provides much of its food. Few birds could make so striking an entrance without singing a note.',
    'A clay figure bares a fearsome set of fangs. Its maker gave the creature enough presence to trouble a stranger centuries later. Guardian, spirit or story made solid? The object leaves room for all three questions.',
    "Reports describe an enormous sloth walking on the ground, with great claws and a heavy tail. Its size sounds like a sailor's embellishment. Yet the forests are wide, and the expedition has searched only a little of them.",
    'A long snout and sweeping tongue help the anteater search for insects. Powerful claws open their defenses, making teeth unnecessary. Few animals arrive at a meal with such specialized equipment.',
    'A colony of flightless seabirds gathers along the cold shore. Leon penguins walk awkwardly on land, then move through the water with startling grace. Their true element becomes obvious the moment they dive.',
    "A small bat feeds by lapping blood from a wound. The vampire bat's habits are unsettling, but its meal is far smaller than fearful stories suggest. A careful naturalist records the animal, not merely its reputation.",
    'High in the Andes, Lake Titicaca stretches beneath a vast sky. Its islands hold deep religious importance in Andean and Inca traditions. The thin air and distant shores make the waters seem suspended between earth and heaven.',
    'A temple dedicated to the sun rises above the surrounding country. Steps, terraces and sacred spaces reveal the labor invested in worship. Watching the light cross its stones, a visitor can understand the choice of deity.',
    "An intricately worked terracotta figure survives where its maker's name has not. Clothing and ornaments give the small form a lively presence. In a few handfuls of fired earth, an unknown artist preserved a whole personality.",
    'A remarkably round stone sphere rests amid the greenery. Shaping and moving it demanded effort, yet its purpose remains uncertain. The smooth surface offers excellent evidence of skill and very little explanation.',
    'Painted figures cover the walls at Marnalico, their poses suggesting ceremony and conflict. Faded colors still carry remarkable energy. Without a guide to their meaning, the expedition can admire far more than it can explain.',
    "The Popol Vuh preserves K'iche' Maya accounts of creation and the adventures of the Hero Twins. Its stories give the world a vivid beginning. A wise collector listens for their meaning as carefully as for unfamiliar names.",
    'A skull carved from clear crystal gleams in the light. Its workmanship is striking, but its origin is uncertain. An extraordinary object deserves close study before an equally extraordinary story is accepted.',
    'A great stone face meets the traveler with an unreadable expression. Its features survive long after the world of its makers has changed. Recording every detail may prove wiser than guessing whom it represents.',
    'The carved Sun Stone gathers powerful symbols around a central face. Its imagery concerns time and the order of the cosmos. To understand its cycles would require far more than counting the marks around the edge.',
    'Beadlike scales cover this thick-bodied lizard. Its heavy appearance conceals a venomous bite, so a respectful distance is essential. A beautiful pattern is no promise of a harmless specimen.',
    'Bison move across the grasslands in great herds, their shaggy forequarters unmistakable. They provide food, hides and other necessities to many Indigenous peoples. Here, the life of the plains depends on more than the grass.',
    'A prairie dog stands upright beside its burrow, keeping watch over the open ground. A sudden warning sends its neighbors below. This small rodent has made vigilance a matter for the whole settlement.',
    'Borobudur rises in terraces of carved stone, leading upward past reliefs and rows of stupas. Buddhist teachings shape the journey through the monument. Reaching the top is both a climb and a lesson.',
    'A python lies coiled among warm branches. It overpowers prey by constriction and swallows its meal whole. The stillness is deceptive: this quiet length of patterned scales is a capable hunter.',
    'A huge monitor lizard crosses the island ground, testing the air with its tongue. The Komodo dragon can tackle substantial prey. Its heavy stride is an impressive sight, especially from a sensible distance.',
    'A kangaroo bounds across open country on powerful hind legs. Its tail helps balance the body, while the young ride in a pouch. The first sight of such a traveler leaves even seasoned sailors searching for comparisons.',
    'A lizard suddenly spreads a broad frill around its head. The display makes a small creature look considerably more formidable. Having delivered its warning, it would probably prefer the expedition to move along.',
    "Uluru rises as an immense red rock above the plain. Sacred to the Anangu people, it holds stories far older than the expedition's charts. Changing light brings new colors to a landmark that rewards patient watching.",
    'Harsh cries emerge from the darkness, followed by a stocky marsupial with powerful jaws. The Tasmanian devil feeds readily on carrion. Its alarming voice sounds far larger than the animal making it.',
    'A koala rests among eucalyptus branches, waking to feed on tough leaves. Its young begin with milk before adapting to this demanding diet. The quiet animal has made a remarkably specialized home in the treetops.',
    "A kiwi searches the ground at night with its long bill. This flightless bird has nostrils near the bill's tip, an unusual aid to finding food. In the darkness, a keen nose can matter more than wings.",
    'A male bird of paradise displays extravagant plumes among the forest branches. The brilliant feathers serve courtship rather than comfortable travel. A naturalist may sketch the display; a sailor can only envy the finery.',
    'A monumental Buddha has been carved into the rock, turning a cliff into a place of contemplation. The scale is astonishing, but the expression remains calm. Many hands must have labored to create so quiet a presence.',
    "Pitcher-shaped leaves hold liquid beneath inviting rims. Insects that slip inside may become food for the plant. The forest's most elegant little cups are far less hospitable than they appear.",
    'A slender tree snake follows a branch so closely that it nearly disappears into the foliage. Its body seems made for this narrow road above the ground. The forest has travelers at every height.',
    'A spiny shell encloses the rich flesh of the durian. Its powerful smell divides the crew before anyone has tasted it. A merchant considering this cargo should choose both customers and storage space carefully.',
    'Island stories describe a giant flightless bird called the moa. Its long legs and great body would make it unlike any familiar fowl. The expedition searches the quiet country with its eyes lowered from the treetops.',
    'A great auk stands upright on the rocky shore, its short wings better suited to swimming than flight. At sea it pursues its food with ease. On land, its solemn appearance gives little hint of that skill.',
    'Pale curtains of light ripple across the northern sky. The aurora shifts and brightens above the dark sea, turning an ordinary watch into a spectacle. No lantern aboard can begin to imitate it.',
    "A huge sea cow grazes in the cold coastal shallows. Its broad body and slow movements give the scene an unexpected gentleness. Among sailors' tales of sea monsters, a quiet eater of marine plants is a welcome change.",
    'A blue whale surfaces beside an immense breath of spray. The largest of animals feeds by filtering tiny prey through baleen plates. Such size sustained by such small meals is a wonder greater than any sea-monster tale.',
    "Northern tales tell of a shaggy elephant with sweeping tusks. The mammoth seems fitted for cold country beyond the expedition's familiar routes. A convincing track would be worth more than a dozen confident stories.",
    "A great cat with extraordinary saberlike teeth appears in travelers' reports. Those curved fangs would make a formidable hunting weapon. The expedition hopes that any closer acquaintance will begin with a distant footprint.",
    "A fruit bat hangs beneath the branches, then takes wing in search of a meal. Fruit, rather than blood, draws its attention. Beneath the unfamiliar face is another participant in the forest's busy harvest.",
    'A cowrie shell shines as though polished by a jeweler. Its smooth shape makes it prized for ornaments and, in some places, exchange. A small object from the sea can travel remarkably far through human hands.',
    'A mouse-like creature supposedly walks upside down upon its nose. The Nasiped taxes belief almost as much as the imagination. The expedition records the tale, while reserving judgment until someone produces a specimen.',
    "A giant tortoise advances beneath its heavy domed shell. Every deliberate step seems to follow a slower clock than the crew's. This island resident offers an excellent subject for an artist with patience.",
    'Moai stand across Rapa Nui, their carved faces looking out with solemn authority. These figures honor ancestors, and many have bodies beneath the familiar heads. Each statue belongs to a landscape filled with meaning.',
)


def validate(value):
    if type(value) is not bool:
        raise ValueError('Rewritten discovery descriptions must be On or Off.')
    return value


def overrides(project):
    if not validate(project.discovery_rewrites):
        return {}
    # A user-created replacement owns its text, even when it uses a stock name.
    return {slot: text for slot, text in enumerate(DESCRIPTIONS)
            if slot not in project.discovery_entries}


def install(data, project):
    texts = overrides(project)
    if not texts:
        return
    if len(data) == 0x200000:
        data.extend(b'\xff' * 0x200000)
        data[0xffd7] = 12
    for slot, text in texts.items():
        if not text or len(text) > 226 or any(not 32 <= ord(c) <= 126 or c == '%' for c in text):
            raise ValueError('Invalid bundled discovery description.')
        raw = text.encode('ascii') + b'\0'
        at = TEXT_BASE + slot * STRIDE
        if data[at:at+len(raw)] != b'\xff' * len(raw):
            raise ValueError('Discovery description storage overlaps another modification.')
        data[at:at+len(raw)] = raw
        pointer = 0xebe62 + slot * 3
        data[pointer:pointer+3] = (0xc00000 + at).to_bytes(3, 'little')
