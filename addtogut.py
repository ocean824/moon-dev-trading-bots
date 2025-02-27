# ============= EDIT THIS GITHUB USERNAME TO ADD/REMOVE =============
GITHUB_USERNAME = "anordinaryjoe"  # 👈 Change this value only!
# =============================================================

from github import Github
import os

def display_menu():
    print("\n🌙 Moon Dev's GitHub Collaborator Manager 3000 🚀")
    print("===============================================")
    print(f"Current GitHub Username: {GITHUB_USERNAME}")
    print("===============================================")
    print("1. Add GitHub collaborator")
    print("2. Remove GitHub collaborator")
    print("3. List current collaborators")
    print("4. Exit")
    return input("Choose an option (1-4): ")

def add_collaborator(repo_name, github_username):
    print(f"🚀 Moon Dev's Collaborator Adding System Initializing...")

    g = Github('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')
    print(f"🔍 Attempting to access repositories...")

    try:
        # Let's verify our authentication first
        user = g.get_user()
        print(f"👤 Authenticated as: {user.login}")

        # Add to first repository
        repo1 = g.get_repo("moondevonyt/moon-dev-ai-agents")
        print(f"📁 Found repository: {repo1.name}")
        repo1.add_to_collaborators(github_username, permission='pull')
        print(f"✅ Successfully added {github_username} to moon-dev-ai-agents!")

        # Add to second repository
        repo2 = g.get_repo("moondevonyt/moon-dev-trading-bots")
        print(f"📁 Found repository: {repo2.name}")
        repo2.add_to_collaborators(github_username, permission='pull')
        print(f"✅ Successfully added {github_username} to moon-dev-trading-bots!")

        print(f"🛡️ They can fork and read the code but cannot modify your main repositories")
        print(f"🌟 Moon Dev's system completed successfully! 🎉")

    except Exception as e:
        if "404" in str(e):
            print(f"❌ ERROR: The username '{github_username}' is invalid or doesn't exist on GitHub!")
            print("💡 Make sure you're using their GitHub username, not their email")
        else:
            print(f"❌ Error occurred: {str(e)}")
        print("💭 Debug info:")
        print(f"   - Attempted repos: moon-dev-ai-agents and moon-dev-trading-bots")
        print(f"   - Attempted to add user: {github_username}")
        print("💫 Moon Dev's error handling caught this one!")

def remove_collaborator(repo_name, github_username):
    print(f"🚀 Moon Dev's Collaborator Removal System Initializing...")

    g = Github('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')
    print(f"🔍 Attempting to access repository: {repo_name}")

    try:
        # Verify authentication
        user = g.get_user()
        print(f"👤 Authenticated as: {user.login}")

        # Get the repository
        repo = g.get_repo("moondevonyt/moon-dev-ai-agents")
        print(f"📁 Found repository: {repo.name}")

        # Remove collaborator
        repo.remove_from_collaborators(github_username)
        print(f"✅ Successfully removed {github_username} from collaborators!")
        print(f"🌟 Moon Dev's system completed successfully! 🎉")

    except Exception as e:
        if "404" in str(e):
            print(f"❌ ERROR: The username '{github_username}' is invalid or not a collaborator!")
            print("💡 Make sure you're using their GitHub username and they are a current collaborator")
        else:
            print(f"❌ Error occurred: {str(e)}")
        print("💭 Debug info:")
        print(f"   - Attempted repo: moondevonyt/moon-dev-ai-agents")
        print(f"   - Attempted to remove user: {github_username}")
        print("💫 Moon Dev's error handling caught this one!")

def list_collaborators(repo_name):
    print(f"🚀 Moon Dev's Collaborator List System Initializing...")

    g = Github('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')
    print(f"🔍 Attempting to access repository: {repo_name}")

    try:
        # Verify authentication
        user = g.get_user()
        print(f"👤 Authenticated as: {user.login}")

        # Get the repository
        repo = g.get_repo("moondevonyt/moon-dev-ai-agents")
        print(f"📁 Found repository: {repo.name}")

        # List collaborators
        print("\n📋 Current Collaborators:")
        print("=======================")
        collaborators = repo.get_collaborators()
        for collab in collaborators:
            print(f"👤 {collab.login}")
        print("=======================")

    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        print("💭 Debug info:")
        print(f"   - Attempted repo: moondevonyt/moon-dev-ai-agents")
        print("💫 Moon Dev's error handling caught this one!")

def main():
    repo_name = "moondevonyt/moon-dev-ai-agents"

    try:
        choice = display_menu()

        if choice == '1':
            add_collaborator(repo_name, GITHUB_USERNAME)

        elif choice == '2':
            remove_collaborator(repo_name, GITHUB_USERNAME)

        elif choice == '3':
            list_collaborators(repo_name)

        elif choice == '4':
            print("👋 Goodbye! Moon Dev's GitHub Manager signing off! 🌙")

        else:
            print("❌ Invalid option! Please try again.")

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

    print("\n✨ Done! Run the script again for more operations!")

if __name__ == "__main__":
    main()