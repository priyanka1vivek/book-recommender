"""
seed.py -- Populates the SQLite database and builds the embedding index.

Run once before starting the server:
    cd backend
    python seed.py

What it does:
  1. Creates the SQLite tables (if they don't exist yet)
  2. Wipes and re-inserts all 40 books (30 English + 5 Hindi + 5 Kannada)
  3. Passes each book's combined text through the BERT model
  4. Saves the resulting 384-float vector into the book's embedding_json column
  5. After this the /recommend/vibe endpoint works immediately

Re-running this script is safe -- it wipes and rebuilds from scratch.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import engine, Base, SessionLocal
from app.models.book import Book
from app.services.embeddings import embed_book
from app.services.recommender import add_book_embedding


# ---------------------------------------------------------------------------
# Curated seed library -- 40 books across 12 languages and genres.
# Descriptions are intentionally long and thematic so the embedding captures
# mood, tone, and atmosphere -- not just surface-level genre keywords.
# ---------------------------------------------------------------------------
BOOKS = [

    # -- LITERARY FICTION (English) -----------------------------------------
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "genre": "Literary Fiction",
        "language": "English",
        "year": 1960,
        "isbn": "9780061935466",
        "description": (
            "In the American Deep South of the 1930s, young Scout Finch watches as her "
            "father, lawyer Atticus Finch, defends a Black man falsely accused of raping "
            "a white woman. A powerful story of racial injustice, moral courage, and the "
            "loss of childhood innocence set against the suffocating backdrop of Southern "
            "segregation. Warm, humane, and devastating."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780061935466-M.jpg",
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "genre": "Dystopian Fiction",
        "language": "English",
        "year": 1949,
        "isbn": "9780451524935",
        "description": (
            "In a totalitarian future state, government surveillance is absolute, "
            "independent thought is a crime called thoughtcrime, and the past is "
            "rewritten daily. Winston Smith secretly rebels against Big Brother's regime, "
            "falls in love, and seeks truth -- while the Thought Police close in. A chilling, "
            "prophetic warning about authoritarianism, propaganda, and the fragility of truth."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780451524935-M.jpg",
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "genre": "Literary Fiction",
        "language": "English",
        "year": 1925,
        "isbn": "9780743273565",
        "description": (
            "In the glittering, gin-soaked excess of 1920s Long Island, mysterious "
            "millionaire Jay Gatsby throws lavish parties hoping to reunite with his lost "
            "love Daisy Buchanan. Narrated by Nick Carraway, this is a dazzling, melancholy "
            "portrait of obsession, wealth, illusion, class, and the hollow promise of the "
            "American Dream. Lyrical and heartbreaking."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780743273565-M.jpg",
    },
    {
        "title": "One Hundred Years of Solitude",
        "author": "Gabriel Garcia Marquez",
        "genre": "Magical Realism",
        "language": "English",
        "year": 1967,
        "isbn": "9780060883287",
        "description": (
            "Seven generations of the Buendia family inhabit the mythical, rain-soaked "
            "town of Macondo, where miracles and catastrophes unfold as naturally as weather. "
            "A multigenerational epic of love, war, passion, and solitude from Nobel laureate "
            "Garcia Marquez. The defining work of magical realism -- where the extraordinary "
            "is treated as mundane and the mundane becomes extraordinary."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780060883287-M.jpg",
    },
    {
        "title": "A Little Life",
        "author": "Hanya Yanagihara",
        "genre": "Literary Fiction",
        "language": "English",
        "year": 2015,
        "isbn": "9780804172707",
        "description": (
            "Four college friends build their adult lives in New York, but the story "
            "belongs entirely to Jude St. Francis, whose unknowable past gradually reveals "
            "itself as a history of devastating abuse and trauma. An unflinching, emotionally "
            "brutal novel about suffering, survival, the limits of friendship, and whether "
            "love can ever be enough. Not for the faint of heart -- but deeply, achingly human."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780804172707-M.jpg",
    },
    {
        "title": "Normal People",
        "author": "Sally Rooney",
        "genre": "Contemporary Fiction",
        "language": "English",
        "year": 2018,
        "isbn": "9780571334650",
        "description": (
            "Connell and Marianne grow up in the same small Irish town but move in "
            "entirely different social worlds. Their complicated, on-off relationship "
            "stretches across years and continents -- cycling through power, desire, "
            "miscommunication, and intimacy. A quiet, precise novel about love's capacity "
            "to simultaneously damage and sustain, told in spare, devastatingly accurate prose."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780571334650-M.jpg",
    },
    {
        "title": "The Kite Runner",
        "author": "Khaled Hosseini",
        "genre": "Literary Fiction",
        "language": "English",
        "year": 2003,
        "isbn": "9781594631931",
        "description": (
            "Amir, the son of a wealthy Kabul merchant, and Hassan, the son of his "
            "servant, are childhood friends whose bond is shattered by a devastating "
            "act of cowardice. Spanning decades from pre-Soviet Afghanistan to "
            "San Francisco, this is a heartrending story of guilt, redemption, betrayal, "
            "and the love between fathers and sons. Deeply emotional and impossible to forget."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781594631931-M.jpg",
    },

    # -- PSYCHOLOGICAL / CRIME THRILLER (English) --------------------------
    {
        "title": "Gone Girl",
        "author": "Gillian Flynn",
        "genre": "Psychological Thriller",
        "language": "English",
        "year": 2012,
        "isbn": "9780307588364",
        "description": (
            "When Amy Dunne vanishes on her fifth wedding anniversary, all signs point "
            "to her charming husband Nick. Told in alternating voices that slowly "
            "contradict each other, this razor-sharp psychological thriller dismantles "
            "the mythology of the perfect marriage and explores media manipulation, "
            "identity performance, and how well we ever really know the people we love. "
            "Dark, twisty, and deeply unsettling."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780307588364-M.jpg",
    },
    {
        "title": "The Girl with the Dragon Tattoo",
        "author": "Stieg Larsson",
        "genre": "Crime Thriller",
        "language": "English",
        "year": 2005,
        "isbn": "9780307949509",
        "description": (
            "Disgraced journalist Mikael Blomkvist teams with brilliant, antisocial "
            "hacker Lisbeth Salander to investigate a forty-year-old disappearance "
            "within one of Sweden's most powerful family dynasties. A dark, cold, "
            "labyrinthine Nordic crime thriller about violence against women, corporate "
            "corruption, and justice delivered outside the broken system. Gripping from page one."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780307949509-M.jpg",
    },
    {
        "title": "Big Little Lies",
        "author": "Liane Moriarty",
        "genre": "Domestic Thriller",
        "language": "English",
        "year": 2014,
        "isbn": "9780425274866",
        "description": (
            "Three mothers at an elite school in coastal Australia are bound together by "
            "a secret that explodes on one fatal trivia night. Sharp, darkly funny, and "
            "genuinely chilling, this novel dissects domestic violence hidden behind "
            "perfect facades, female friendship under pressure, and the explosive "
            "consequences of the truths we bury to survive."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780425274866-M.jpg",
    },
    {
        "title": "In the Woods",
        "author": "Tana French",
        "genre": "Mystery",
        "language": "English",
        "year": 2007,
        "isbn": "9780143113492",
        "description": (
            "Dublin Murder Squad detective Rob Ryan investigates the murder of a girl "
            "at an archaeological dig in the woods -- the same woods where he was the "
            "sole survivor of a traumatic childhood event he cannot remember. A lyrical, "
            "deeply atmospheric mystery drenched in Irish rain and dread, exploring "
            "memory, identity, and the crimes we bury deepest inside ourselves."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780143113492-M.jpg",
    },

    # -- EPIC FANTASY (English) --------------------------------------------
    {
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "genre": "Epic Fantasy",
        "language": "English",
        "year": 2007,
        "isbn": "9780756404741",
        "description": (
            "Kvothe -- the most legendary figure of his age: hero, sorcerer, musician, "
            "and assassin -- sits in a rural inn and begins to narrate the true story of "
            "his extraordinary life to a chronicler. From a wandering childhood among "
            "traveling performers to mastering arcane arts at a magical university, "
            "this is a rich, literate, beautifully written fantasy unlike anything else. "
            "Magic feels real. Loss feels real. Everything feels real."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780756404741-M.jpg",
    },
    {
        "title": "The Way of Kings",
        "author": "Brandon Sanderson",
        "genre": "Epic Fantasy",
        "language": "English",
        "year": 2010,
        "isbn": "9780765326355",
        "description": (
            "On the storm-swept world of Roshar, a war rages on the shattered plains. "
            "A surgeon-turned-slave, a young assassin bound by impossible oaths, and a "
            "noblewoman deciphering ancient secrets are drawn toward the heart of a "
            "civilization-threatening conflict. A meticulously constructed, enormous epic "
            "fantasy with original magic systems, deep world-building, and characters "
            "who earn every moment of their arc."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780765326355-M.jpg",
    },
    {
        "title": "Harry Potter and the Philosopher's Stone",
        "author": "J.K. Rowling",
        "genre": "Fantasy",
        "language": "English",
        "year": 1997,
        "isbn": "9780590353427",
        "description": (
            "On his eleventh birthday, orphan Harry Potter discovers he is a wizard "
            "and has been accepted to Hogwarts School of Witchcraft and Wizardry. "
            "In a magical world hidden within ordinary Britain -- of moving staircases, "
            "talking portraits, and flying broomsticks -- he finds his first real friends, "
            "uncovers a dark conspiracy, and begins his destiny. Pure enchantment that "
            "has captivated generations."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780590353427-M.jpg",
    },
    {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "genre": "Fantasy",
        "language": "English",
        "year": 1937,
        "isbn": "9780547928227",
        "description": (
            "Comfort-loving hobbit Bilbo Baggins is swept into an unexpected adventure "
            "by wizard Gandalf and a company of dwarves seeking to reclaim their mountain "
            "kingdom from the fearsome dragon Smaug. A warm, witty, and deeply adventurous "
            "quest story about unlikely heroism, the wide world beyond one's front door, "
            "and finding courage you never knew you had. The cozy beginning of Middle-earth."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780547928227-M.jpg",
    },

    # -- SCIENCE FICTION (English) -----------------------------------------
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "genre": "Science Fiction",
        "language": "English",
        "year": 1965,
        "isbn": "9780441013593",
        "description": (
            "On Arrakis -- the scorching desert planet and only source of the universe's "
            "most precious substance -- young Paul Atreides navigates deadly political "
            "intrigue between noble houses, ancient religious prophecy, and the fierce "
            "native warriors called Fremen. A sweeping, ecological science fiction epic "
            "about power, religion, colonialism, and human destiny. The best-selling "
            "sci-fi novel of all time."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780441013593-M.jpg",
    },
    {
        "title": "The Hitchhiker's Guide to the Galaxy",
        "author": "Douglas Adams",
        "genre": "Comic Science Fiction",
        "language": "English",
        "year": 1979,
        "isbn": "9780345391803",
        "description": (
            "Seconds before Earth is demolished to make way for a hyperspace bypass, "
            "hapless Arthur Dent is rescued by his alien friend Ford Prefect and swept "
            "into a universe governed by improbability drives, depressed robots, and "
            "officious bureaucratic Vogons. Razor-sharp satirical comedy that skewers "
            "technology, philosophy, and the human condition. The funniest science "
            "fiction ever written."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780345391803-M.jpg",
    },
    {
        "title": "Project Hail Mary",
        "author": "Andy Weir",
        "genre": "Science Fiction",
        "language": "English",
        "year": 2021,
        "isbn": "9780593135204",
        "description": (
            "Ryland Grace wakes up alone on a spaceship millions of miles from Earth "
            "with no memory of who he is or why he's there. As memories piece themselves "
            "together, he realizes he is humanity's last hope against a solar extinction "
            "event -- and then meets an entirely unexpected alien companion. A page-turning, "
            "joyful, rigorously science-driven survival story overflowing with optimism "
            "and wonder."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780593135204-M.jpg",
    },
    {
        "title": "Ender's Game",
        "author": "Orson Scott Card",
        "genre": "Science Fiction",
        "language": "English",
        "year": 1985,
        "isbn": "9780812550702",
        "description": (
            "Gifted child Andrew 'Ender' Wiggin is recruited to an orbital military "
            "school where children are trained through increasingly brutal war simulations "
            "to become commanders against an alien race. A gripping, morally complex "
            "exploration of genius, child prodigies, military ethics, manipulation, and "
            "the devastating psychological cost of being humanity's last hope."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780812550702-M.jpg",
    },

    # -- ROMANCE (English) -------------------------------------------------
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "genre": "Romance",
        "language": "English",
        "year": 1813,
        "isbn": "9780141439518",
        "description": (
            "Clever, spirited Elizabeth Bennet navigates the rigid marriage market of "
            "Regency England, engaged in a battle of wits and misunderstandings with the "
            "proud, wealthy Mr. Darcy. A sparkling, endlessly re-readable love story "
            "about first impressions, class prejudice, family pressure, and learning to "
            "see past your own most stubborn assumptions. Austen's masterpiece."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780141439518-M.jpg",
    },
    {
        "title": "Outlander",
        "author": "Diana Gabaldon",
        "genre": "Historical Romance",
        "language": "English",
        "year": 1991,
        "isbn": "9780385319959",
        "description": (
            "In 1945 Scotland, combat nurse Claire Randall touches an ancient standing "
            "stone and is transported to 1743, where she is caught between a brutal "
            "British officer and passionate Highland warrior Jamie Fraser. A sweeping, "
            "immersive historical romance combining time travel, Jacobite uprising, "
            "visceral adventure, and the most intense love affair in historical fiction."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780385319959-M.jpg",
    },
    {
        "title": "The Notebook",
        "author": "Nicholas Sparks",
        "genre": "Romance",
        "language": "English",
        "year": 1996,
        "isbn": "9781455582877",
        "description": (
            "An old man reads daily from a notebook to a woman in a nursing home -- "
            "the story of two young lovers in 1940s North Carolina kept apart by "
            "family, class, and circumstance but unable to stay apart. A simple, deeply "
            "emotional love story about devotion, memory, and a love so profound it can "
            "briefly pierce even the fog of dementia. Tender and tearful."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781455582877-M.jpg",
    },

    # -- HORROR (English) --------------------------------------------------
    {
        "title": "The Shining",
        "author": "Stephen King",
        "genre": "Horror",
        "language": "English",
        "year": 1977,
        "isbn": "9780385121675",
        "description": (
            "Recovering alcoholic writer Jack Torrance takes a winter caretaker job at "
            "the remote, snowbound Overlook Hotel with his wife Wendy and young son Danny, "
            "who possesses a psychic gift called 'the shining.' As winter seals them in, "
            "the hotel's malevolent supernatural history slowly invades Jack's mind, "
            "driving him toward violence. King's most psychologically devastating "
            "masterpiece -- a study of isolation, addiction, and domestic terror."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780385121675-M.jpg",
    },
    {
        "title": "It",
        "author": "Stephen King",
        "genre": "Horror",
        "language": "English",
        "year": 1986,
        "isbn": "9781501156700",
        "description": (
            "In the town of Derry, Maine, a shapeshifting ancient evil that often takes "
            "the form of a clown named Pennywise has been killing children for centuries. "
            "A group of seven childhood misfits who once defeated It are forced to return "
            "as adults when It awakens again. Told across two timelines, this massive, "
            "terrifying, and deeply emotional novel is ultimately about the bonds of "
            "childhood friendship and the monsters we carry into adulthood."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781501156700-M.jpg",
    },

    # -- HISTORICAL FICTION (English) --------------------------------------
    {
        "title": "All the Light We Cannot See",
        "author": "Anthony Doerr",
        "genre": "Historical Fiction",
        "language": "English",
        "year": 2014,
        "isbn": "9781476746586",
        "description": (
            "Set across World War II, a blind French girl living in German-occupied "
            "Saint-Malo and a German orphan boy recruited into the Nazi war machine "
            "are drawn inexorably toward each other by fate and a legendary diamond. "
            "A Pulitzer Prize-winning novel of breathtaking prose beauty about "
            "survival, the human cost of war, and the small lights of kindness and "
            "curiosity that keep us human in the darkest of times."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781476746586-M.jpg",
    },
    {
        "title": "The Pillars of the Earth",
        "author": "Ken Follett",
        "genre": "Historical Fiction",
        "language": "English",
        "year": 1989,
        "isbn": "9780451166890",
        "description": (
            "In 12th-century England, master builder Tom Builder dreams of constructing "
            "a cathedral while monks, nobles, clergy, and peasants engage in decades of "
            "power struggles, war, love, murder, and betrayal. An enthralling, densely "
            "plotted historical saga about cathedral building, medieval politics, faith, "
            "and the indomitable human drive to create something beautiful that will "
            "outlast your own life."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780451166890-M.jpg",
    },
    {
        "title": "Wolf Hall",
        "author": "Hilary Mantel",
        "genre": "Historical Fiction",
        "language": "English",
        "year": 2009,
        "isbn": "9780312429980",
        "description": (
            "The astonishing rise of Thomas Cromwell -- a blacksmith's son who becomes "
            "the most powerful man in England under the mercurial Henry VIII -- told "
            "with razor-sharp psychological intimacy from inside Cromwell's own clever, "
            "watchful mind. A Booker Prize-winning novel of immense depth, Tudor court "
            "intrigue, and cinematic present-tense immediacy."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780312429980-M.jpg",
    },

    # -- NON-FICTION / SELF-HELP (English) ---------------------------------
    {
        "title": "Sapiens: A Brief History of Humankind",
        "author": "Yuval Noah Harari",
        "genre": "Non-Fiction",
        "language": "English",
        "year": 2011,
        "isbn": "9780062316097",
        "description": (
            "A sweeping, provocative narrative of human history from the cognitive "
            "revolution that separated Homo sapiens from other animals 70,000 years ago "
            "to the present age of artificial intelligence and genetic engineering. Harari "
            "examines how shared myths, biology, culture, religion, and economics shaped "
            "civilization and poses urgent, uncomfortable questions about what makes us "
            "human and where we are heading next."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780062316097-M.jpg",
    },
    {
        "title": "Atomic Habits",
        "author": "James Clear",
        "genre": "Self-Help",
        "language": "English",
        "year": 2018,
        "isbn": "9780735211292",
        "description": (
            "A practical, science-backed system for building good habits and breaking "
            "bad ones, rooted in the philosophy that tiny 1% daily improvements compound "
            "into remarkable life changes over time. Clear explains the cue-craving-"
            "response-reward loop that governs all human behavior and shows how to "
            "redesign your environment and identity to make good habits inevitable and "
            "bad habits nearly impossible."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780735211292-M.jpg",
    },
    {
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "genre": "Inspirational Fiction",
        "language": "English",
        "year": 1988,
        "isbn": "9780062315007",
        "description": (
            "Young Spanish shepherd Santiago travels from Andalusia to the Egyptian "
            "desert in pursuit of a recurring dream about treasure, guided by a series "
            "of mystical encounters including a wise alchemist. A beloved, lyrical "
            "philosophical fable about listening to your heart, following your personal "
            "legend, and how the universe conspires to help those who dare to pursue "
            "their dreams. One of the best-selling books in history."
        ),
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780062315007-M.jpg",
    },

    # -- HINDI LITERATURE --------------------------------------------------
    {
        "title": "Godan",
        "author": "Munshi Premchand",
        "genre": "Literary Fiction",
        "language": "Hindi",
        "year": 1936,
        "isbn": None,
        "description": (
            "The story of Hori, a desperately poor farmer in rural India whose "
            "lifelong dream is to own a cow -- a symbol of dignity and prosperity "
            "forever just out of reach. His gradual destruction by debt, caste "
            "oppression, and a system rigged against him is one of literature's most "
            "moving portraits of rural poverty. Considered the greatest Hindi novel "
            "ever written -- Premchand's unflinching masterpiece."
        ),
        "cover_url": "https://covers.openlibrary.org/b/id/8231856-M.jpg",
    },
    {
        "title": "Raag Darbari",
        "author": "Shrilal Shukla",
        "genre": "Satirical Fiction",
        "language": "Hindi",
        "year": 1968,
        "isbn": None,
        "description": (
            "A young man from Delhi visits his uncle's village and discovers the "
            "absurd, corrupt machinery of rural Indian politics -- incompetent officials, "
            "rigged elections, and power games dressed in idealistic language. "
            "A biting, darkly funny satire on bureaucracy and small-town hypocrisy "
            "that remains devastatingly relevant today. Winner of the Sahitya Akademi Award."
        ),
        "cover_url": None,
    },
    {
        "title": "Tamas",
        "author": "Bhisham Sahni",
        "genre": "Historical Fiction",
        "language": "Hindi",
        "year": 1974,
        "isbn": None,
        "description": (
            "Set over five terrifying days during the Partition of India in 1947, "
            "this novel follows ordinary Hindus, Muslims, and Sikhs swept into "
            "communal violence they never chose and cannot stop. Based on the author's "
            "own experience of Partition, it is one of the most devastating and human "
            "accounts of that catastrophic rupture in history -- quiet lives shattered "
            "by forces beyond anyone's control."
        ),
        "cover_url": None,
    },
    {
        "title": "Nirmala",
        "author": "Munshi Premchand",
        "genre": "Social Fiction",
        "language": "Hindi",
        "year": 1925,
        "isbn": None,
        "description": (
            "Nirmala, a young woman whose family cannot afford a dowry, is married "
            "off to a much older widower with children her own age. She navigates "
            "the suffocating suspicion, isolation, and quiet cruelty of her new home "
            "with no recourse and no escape. A searing, compassionate critique of "
            "the dowry system and the silencing of women in traditional Indian society."
        ),
        "cover_url": None,
    },
    {
        "title": "Madhushala",
        "author": "Harivansh Rai Bachchan",
        "genre": "Poetry",
        "language": "Hindi",
        "year": 1935,
        "isbn": None,
        "description": (
            "A celebrated sequence of quatrains in which the tavern, the wine cup, "
            "the beloved, and the innkeeper become extended metaphors for spiritual "
            "seeking, life's transience, and the breaking of caste and religious barriers. "
            "Philosophical, lyrical, and intoxicating -- one of the most memorised and "
            "beloved works in all of Hindi literature, recited across generations."
        ),
        "cover_url": None,
    },

    # -- KANNADA LITERATURE ------------------------------------------------
    {
        "title": "Samskara",
        "author": "U.R. Ananthamurthy",
        "genre": "Literary Fiction",
        "language": "Kannada",
        "year": 1965,
        "isbn": None,
        "description": (
            "When a heretical Brahmin scholar dies in a remote agrahara, no one will "
            "perform his last rites and risk ritual pollution. The protagonist, a "
            "revered Brahmin himself, is forced to confront questions of purity, desire, "
            "and what it truly means to be human. A landmark of Indian literature that "
            "dismantles caste orthodoxy with moral and intellectual force. Translated "
            "into over a dozen languages. Jnanpith Award winner."
        ),
        "cover_url": None,
    },
    {
        "title": "Parva",
        "author": "S.L. Bhyrappa",
        "genre": "Historical Fiction",
        "language": "Kannada",
        "year": 1979,
        "isbn": None,
        "description": (
            "A bold retelling of the Mahabharata stripped of mythology, imagining "
            "what the great war and its legendary figures might have looked like as "
            "historical human beings -- flawed, political, and driven by earthly "
            "desires rather than divine destiny. One of the most ambitious and "
            "widely-read novels in any Indian language, running to over 900 pages "
            "of dense, human drama."
        ),
        "cover_url": None,
    },
    {
        "title": "Mookajjiya Kanasugalu",
        "author": "K. Shivaram Karanth",
        "genre": "Literary Fiction",
        "language": "Kannada",
        "year": 1968,
        "isbn": None,
        "description": (
            "The inner life and prophetic dreams of Mookajji, an old illiterate woman "
            "who processes the rapidly changing world around her through folk memory, "
            "instinct, and earthy wisdom. A lyrical, deeply compassionate portrait of "
            "vanishing coastal Karnataka and the wisdom that modernity is discarding. "
            "Winner of the Jnanpith Award -- one of the tenderest novels in Indian literature."
        ),
        "cover_url": None,
    },
    {
        "title": "Karvalo",
        "author": "Poornachandra Tejaswi",
        "genre": "Adventure",
        "language": "Kannada",
        "year": 1980,
        "isbn": None,
        "description": (
            "Two friends in the rain-soaked coffee-estate country of Malnad pursue "
            "a mythical creature said to glow in the dark, stumbling through jungles "
            "and eccentric encounters along the way. Part ecological thriller, part "
            "comedy, part nature writing -- a warm and funny Kannada novel that "
            "captures the magic and biodiversity of the Western Ghats with rare wonder."
        ),
        "cover_url": None,
    },
    {
        "title": "Aavarana",
        "author": "S.L. Bhyrappa",
        "genre": "Historical Fiction",
        "language": "Kannada",
        "year": 2007,
        "isbn": None,
        "description": (
            "A filmmaker discovers her husband is systematically erasing evidence of "
            "iconoclasm in medieval India to fit a political narrative. Told through a "
            "novel-within-a-novel structure, this deeply researched and controversial "
            "book interrogates historical truth, identity, and the politics of cultural "
            "memory. It sparked intense national debate about what gets remembered "
            "and what gets buried."
        ),
        "cover_url": None,
    },
]


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------
def main():
    print("\n" + "=" * 60)
    print("  BOOK RECOMMENDER -- DATABASE SEEDER")
    print("=" * 60)

    # Step 1: Create SQLite tables
    print("\n[1/4] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("      SQLite tables ready.")

    # Step 2: Clear old data for a clean rebuild
    print("\n[2/4] Clearing old books and embeddings...")
    db = SessionLocal()

    try:
        deleted = db.query(Book).delete()
        db.commit()
        if deleted:
            print(f"      Cleared {deleted} existing book(s).")

        # Step 3: Insert all books into SQLite
        print("\n[3/4] Inserting books into SQLite...")
        books_to_embed = []
        for data in BOOKS:
            book = Book(**data)
            db.add(book)
            books_to_embed.append(book)

        db.flush()   # assigns IDs without committing
        db.commit()
        print(f"      {len(books_to_embed)} books saved to SQLite.")

        # Step 4: Generate embeddings
        print(f"\n[4/4] Generating embeddings (30-60s on first run)...")
        for i, book in enumerate(books_to_embed, 1):
            embedding = embed_book(
                title=book.title,
                author=book.author,
                description=book.description,
                genre=book.genre,
            )
            add_book_embedding(book_id=book.id, embedding=embedding, db=db)
            bar = "#" * i + "." * (len(books_to_embed) - i)
            lang = f"[{book.language}]" if book.language else ""
            print(
                f"\r      [{bar}] {i}/{len(books_to_embed)}  "
                f"{book.title[:32]:<32} {lang}",
                end=""
            )

        db.commit()
        print("\n")

    finally:
        db.close()

    english = sum(1 for b in BOOKS if b.get("language") == "English")
    hindi   = sum(1 for b in BOOKS if b.get("language") == "Hindi")
    kannada = sum(1 for b in BOOKS if b.get("language") == "Kannada")

    print("=" * 60)
    print(f"  [OK] {len(BOOKS)} books embedded and indexed.")
    print(f"       English: {english}  Hindi: {hindi}  Kannada: {kannada}")
    print("  [OK] Start the server:")
    print("       uvicorn app.main:app --reload --port 8000")
    print("  [OK] API docs: http://localhost:8000/docs")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
