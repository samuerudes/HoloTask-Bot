import settings
import discord
import firebase_admin
from discord.ext import commands
from firebase_admin import firestore
from firebase_admin import credentials
from datetime import datetime
from datetime import timedelta
import asyncio
import uuid

logger = settings.logging.getLogger("bot")


def run():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    cred = credentials.Certificate('holotask-888e5-firebase-adminsdk-gdej4-4134ae64e7.json')

    # Initialize Firebase only if it hasn't been initialized yet
    if not firebase_admin._apps:  # Check if any Firebase apps exist
        firebase_admin.initialize_app(cred)

    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user} (ID: {bot.user.id})")

    @bot.command(name="tasks")
    async def tasks(ctx):
        """Retrieves tasks for the user who invoked the command, sorted by status and end date."""

        try:
            db = firestore.client()
            user_discord = str(ctx.author.id)
            users_ref = db.collection('Users')
            query = users_ref.where('userDiscord', '==', user_discord)
            documents = query.stream()

            # Check if there are any matching documents
            user_doc = None
            for doc in documents:
                user_doc = doc
                break

            if not user_doc:
                await ctx.send(f"Cannot find user with Discord ID: {user_discord}\nPlease enter your Discord ID in in HoloTask > Account Details.")
                return

            user_data = user_doc.to_dict()
            username = user_data.get('userName')
            user_tasks = f"Tasks for user **{username}**:\n-------------------------------\n"

            usertasks_ref = db.collection('UserTasks')

            # Sort tasks by endDateTime (ascending) and taskStatus ('overdue', 'ongoing', 'complete')
            query2 = usertasks_ref.where('userId', '==', user_doc.id)
            query2 = query2.order_by('taskStatus', direction=firestore.Query.DESCENDING)  # Order by taskStatus first
            query2 = query2.order_by('endDateTime', direction=firestore.Query.ASCENDING)  # Then order by endDateTime

            documents2 = query2.stream()

            for doc2 in documents2:
                usertask_data = doc2.to_dict()
                task_status = usertask_data['taskStatus'].upper()  # Make status bold

                user_tasks += f"Name: {usertask_data['taskName']}\n"
                user_tasks += f"Status: **{task_status}**\n"
                user_tasks += f"End Date: {usertask_data['endDateTime']}\n"
                user_tasks += f"Description: {usertask_data['taskDescription']}\n-------------------------------\n"

            await ctx.send(user_tasks)

            logger.info(f"Task retrieval for user {user_doc.id} is successful.")

        except Exception as e:
            await ctx.send(f"An error occurred while retrieving tasks: {e}")
            logger.error(f"Error retrieving tasks for user {username}: {e}")

    @bot.command(name="create")
    async def create(ctx):
        """Command to create a new task."""

        # Check if user is registered
        db = firestore.client()
        user_discord = str(ctx.author.id)
        users_ref = db.collection('Users')
        query = users_ref.where('userDiscord', '==', user_discord)
        user_docs = query.stream()

        user_doc = None
        for doc in user_docs:
            user_doc = doc
            break

        if not user_doc:
            await ctx.send(f"Cannot find user with Discord ID: {user_discord}\nPlease enter your Discord ID in HoloTask > Account Details.")
            return

        await ctx.send("__Please enter your task details__")

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            await ctx.send("Task Name:")
            task_name_msg = await bot.wait_for('message', check=check, timeout=20)
            task_name = task_name_msg.content.strip()

            await ctx.send("Task Description:")
            task_desc_msg = await bot.wait_for('message', check=check, timeout=20)
            task_description = task_desc_msg.content.strip()

            valid_date_format = False
            while not valid_date_format:
                await ctx.send("Task End Date (DD/MM/YYYY):")
                task_end_date_msg = await bot.wait_for('message', check=check, timeout=20)
                task_end_date_str = task_end_date_msg.content.strip()

                try:
                    task_end_date = datetime.strptime(task_end_date_str, '%d/%m/%Y')
                    # Function to format date if needed
                    def format_date(date_str):
                        try:
                            return datetime.strptime(date_str, '%d/%m/%Y').strftime('%d/%m/%Y')
                        except ValueError:
                            return None
                    task_end_date_str = format_date(task_end_date_str)
                    valid_date_format = True
                except ValueError:
                    await ctx.send("Invalid date format. Please try again using DD/MM/YYYY format (e.g. 01/01/2024).")

            # Parse end date from user input
            task_end_date = datetime.strptime(task_end_date_str, '%d/%m/%Y')
            current_date = datetime.now()
            current_date_minus_one_day = current_date - timedelta(days=1)  # Add one day to current date

            if task_end_date > current_date_minus_one_day:
                task_status = 'Ongoing'
            else:
                task_status = 'Overdue'

            confirmation_message = (
                f"__**Please confirm the task details to add task (Y/N)?**__\n"
                f"Name: {task_name}\n"
                f"Status: **{task_status.upper()}**\n"
                f"End Date: {task_end_date_str}\n"
                f"Description: {task_description}\n\n"
            )
        
            await ctx.send(confirmation_message)

            confirm_msg = await bot.wait_for('message', check=check, timeout=20)
            confirmation = confirm_msg.content.strip().lower()

            user_data = user_doc.to_dict()
            username = user_data.get('userName')

            if confirmation == 'y':
                # Generate task ID
                task_id = uuid.uuid4().hex

                # Store task in Firestore
                usertasks_ref = db.collection('UserTasks')
                task_data = {
                    'userId': user_doc.id,
                    'taskName': task_name,
                    'taskDescription': task_description,
                    'endDateTime': task_end_date_str,
                    'taskStatus': task_status,
                    'taskID': task_id
                }
                usertasks_ref.add(task_data)

                await ctx.send(f"Task for user {username} is created!")
        
                logger.info(f"Task creation for user {username} complete.")

            elif confirmation == 'n':
                await ctx.send(f"Task creation for user {username} cancelled.")
                logger.info(f"Task creation for user {username} cancelled.")

        except asyncio.TimeoutError:
            await ctx.send("Task creation timed out. Please try again.")
            logger.info("Timed out.")

        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            logger.info(f"Task creation for user {username} failed.")

    @bot.command(name="ping")
    async def ping(ctx):
        """Ping command to test bot responsiveness."""
        await ctx.send("Pong")

    bot.run(settings.DISCORD_API_SECRET, root_logger=True)

if __name__ == "__main__":
    run()
