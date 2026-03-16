from agent import create_agent

def main():
    agent = create_agent()

    query = """
    Find evidence about mRNA vaccines for influenza and summarize the findings
    """

    results = agent.invoke({"input": query})

    print("\nFINAL REPORT\n")
    print(results["output"])

if __name__=="__main__":
    main()