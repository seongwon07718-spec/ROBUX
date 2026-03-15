if __name__ == "__main__":
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    web_p = multiprocessing.Process(target=lambda: uvicorn.run(app, host="0.0.0.0", port=88))
    web_p.start()
    web_p.terminate()
    
    bot.run("MTQ3NzY2Mjg3MTIwNTcxMjA3OQ.GvFnzw.qMYsMr_-LODzECKnYY")
