import re
import os
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import openai
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger
from datetime import datetime, timedelta, timezone
import tools_00 as tls

# Get the current date and time
current_datetime = datetime.now(tz=timezone(timedelta(hours=3)))

# Format the date and time as a string
formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")

csvfilename = "Logs/" + formatted_datetime + "_answers.csv"

load_dotenv()
# Загрузка значений из .env
API_KEY = os.environ.get("API_KEY")
os.environ["OPENAI_API_KEY"] = API_KEY
openai.api_key = API_KEY
client = OpenAI(
    api_key=openai.api_key
)

PROMPT = None
KNOWLEDGE_BASE = None

DATA_FILES = os.environ.get("DATA_FILES")
logger.debug (f'DATA_FILES = {DATA_FILES}')

if DATA_FILES == 'local':
    SYSTEM_DOC_LOCAL = os.environ.get("SYSTEM_DOC_LOCAL")
    logger.debug(f'SYSTEM_DOC_LOCAL={SYSTEM_DOC_LOCAL}')
    KNOWLEDGE_BASE_LOCAL = os.environ.get("KNOWLEDGE_BASE_LOCAL")
    logger.debug(f'KNOWLEDGE_BASE_LOCAL={KNOWLEDGE_BASE_LOCAL}')

LL_MODEL = os.environ.get("LL_MODEL") # модель
logger.debug(f'LL_MODEL = {LL_MODEL}')

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE")) # Количество токинов в  чанке
logger.debug(f'CHUNK_SIZE={CHUNK_SIZE}')

NUMBER_RELEVANT_CHUNKS = int(os.environ.get("NUMBER_RELEVANT_CHUNKS"))   # Количество релевантных чанков
logger.debug(f'NUMBER_RELEVANT_CHUNKS={NUMBER_RELEVANT_CHUNKS}')

TEMPERATURE = float(os.environ.get("TEMPERATURE")) # Температура модели
logger.debug(f'TEMPERATURE={TEMPERATURE}')

SYSTEM_DOC_URL = os.environ.get("SYSTEM_DOC_URL") # промпт
logger.debug(f'SYSTEM_DOC_URL = {SYSTEM_DOC_URL}')

KNOWLEDGE_BASE_URL = os.environ.get("KNOWLEDGE_BASE_URL") # база знаний
logger.debug(f'KNOWLEDGE_BASE_URL = {KNOWLEDGE_BASE_URL}')


# Записывам в файл заголовок
tls.write_to_file('user_id;user_name;question;answer', csvfilename)

def reload_data():
    logger.debug('reload_data')
    # Инструкция для GPT, которая будет подаваться в system
    if DATA_FILES == 'local':
        prompt = tls.load_text(SYSTEM_DOC_LOCAL)
    else:
        prompt = tls.load_document_text(SYSTEM_DOC_URL)  # Загрузка файла с Промтом
    logger.debug(f'{prompt}')

    knowledge_base = create_index_db()
    return prompt, knowledge_base


# Функция создания индексной базы знаний
def create_index_db():
    # База знаний, которая будет подаваться в LangChain
    if DATA_FILES == 'local':
        database = tls.load_text(KNOWLEDGE_BASE_LOCAL)
    else:
        database = tls.load_document_text(KNOWLEDGE_BASE_URL)  # Загрузка файла с Базой Знаний
    logger.debug(f'{database}')

    source_chunks = []
    splitter = CharacterTextSplitter(separator="\n", chunk_size=CHUNK_SIZE, chunk_overlap=0)

    for chunk in splitter.split_text(database):
        source_chunks.append(Document(page_content=chunk, metadata={}))

    chunk_num = len(source_chunks)
    logger.debug(f'{chunk_num}')

    # Инициализирум модель эмбеддингов
    embeddings = OpenAIEmbeddings()

    try:
        db = FAISS.from_documents(source_chunks, embeddings) # Создадим индексную базу из разделенных фрагментов текста
    except Exception as e: # обработка ошибок openai.error.RateLimitError
        logger.error(f'!!! External error: {str(e)}')

    for chunk in source_chunks:  # Поиск слишком больших чанков
        if len(chunk.page_content) > CHUNK_SIZE:
            logger.warning(f'*** Слишком большой кусок! ***')
            logger.warning(f'chunk_len ={len(chunk.page_content)}')
            logger.warning(f'content ={chunk.page_content}')

    return db


PROMPT, KNOWLEDGE_BASE = reload_data()

# Запрос в ChatGPT
def get_answer(topic, user_id, user_name):

    # Поиск релевантных отрезков из базы знаний
    docs = KNOWLEDGE_BASE.similarity_search(topic, k = NUMBER_RELEVANT_CHUNKS)

    message_content = re.sub(r'\n{2}', ' ', '\n '.join([f'\n#### Document excerpt №{i+1}####\n' + doc.page_content + '\n' for i, doc in enumerate(docs)]))
    logger.debug(f'{message_content}')

    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": f"Here is the document with information to respond to the client: {message_content}\n\n Here is the client's question: \n{topic}"}
    ]

    logger.debug(f'{messages}')
    num_tokens = tls.num_tokens_from_messages(messages, LL_MODEL)
    logger.debug(f'{num_tokens}')

    try:

        completion = client.chat.completions.create(
            model=LL_MODEL,
            messages=messages,
            temperature=TEMPERATURE
        )
    except Exception as e:  # обработка ошибок openai.error.RateLimitError
        logger.error(f'!!! External error: {str(e)}')

    logger.debug(f'{completion}')
    answer = completion.choices[0].message.content
    line_for_file = '"' + user_id + '";"' + user_name + '";"' + topic + '";"' + answer + '"'
    tls.append_to_file(line_for_file, csvfilename)

    return answer, completion  # возвращает ответ

def answer_user_question(topic, user_name='UserName', user_id='000000'):
    ans, completion = get_answer(topic, user_id, user_name)  # получите ответ модели
    logger.debug(f'ans={ans}')

    return ans


if __name__ == '__main__':
    topic = 'Привет! Ты кто?'
    logger.debug(f'topic={topic}')
    response = answer_user_question(topic)
    logger.debug(f'response={response}')





